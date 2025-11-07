# CityFlow — uruchomienie na Windows 11 (Docker Desktop, Python 3.10)

Ten przewodnik opisuje sprawdzone kroki potrzebne do uruchomienia CityFlow pod Windows 11 z Docker Desktop, korzystając z własnego obrazu (Ubuntu 22.04, Python 3.10). Dodatkowo pozostaje opcjonalny obraz legacy z repo (Ubuntu 16.04, Python 3.6) jako fallback.

---

## 0. Wymagania

- Windows 11 z zainstalowanym Docker Desktop (WSL2).
- Udostępniony dysk `C:` w Docker Desktop  
  (Settings → Resources → File Sharing → `C:` zaznaczone).
- Git (do klonowania repozytorium).

---

## 1. Sklonuj repozytorium z submodułami

```powershell
cd C:\Users\antek\Desktop
git clone https://github.com/cityflow-project/CityFlow.git
cd C:\Users\antek\Desktop\CityFlow
git submodule update --init --recursive
```

---

## 2. (Opcjonalnie) zbuduj obraz legacy (Ubuntu 16.04 + Python 3.6)

```powershell
docker build -f Dockerfile -t cityflow:legacy .
docker run -it --rm cityflow:legacy `
  python -c "import cityflow,sys; print('CityFlow import OK; Python', sys.version)"
```

---

## 3. Zbuduj nowoczesny obraz `cityflow:py310` (Ubuntu 22.04 + Python 3.10)

### 3.1 Utwórz plik `Dockerfile.py310`

`C:\Users\antek\Desktop\CityFlow\Dockerfile.py310`:

```Dockerfile
FROM ubuntu:22.04
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential cmake git curl ca-certificates \
    python3 python3-pip python3-venv python3-dev \
 && rm -rf /var/lib/apt/lists/*

RUN useradd -ms /bin/bash dev
USER dev
WORKDIR /home/dev/app

RUN python3 -m venv .venv
ENV PATH="/home/dev/app/.venv/bin:$PATH"
RUN pip install --upgrade pip wheel setuptools

CMD ["/bin/bash"]
```

### 3.2 Zbuduj obraz

```powershell
docker build -f Dockerfile.py310 -t cityflow:py310 .
```

---

## 4. Uruchom kontener z montowaniem repozytorium

W Docker Desktop używaj ścieżek `//c/...` (lub `/host_mnt/c/...`), nie `/mnt/c/...`.

```powershell
docker run -it --rm -u root `
  -v "//c/Users/antek/Desktop/CityFlow:/home/dev/app" `
  cityflow:py310 bash
```

Flaga `-u root` gwarantuje prawa zapisu do katalogu montowanego z NTFS (potrzebne do utworzenia `.venv`). Po starcie jesteś w `/home/dev/app` (to montowane repo z Windowsa).

---

## 5. Utwórz i aktywuj wirtualne środowisko, zainstaluj CityFlow

W terminalu kontenera:

```bash
python3 -m venv .venv
. .venv/bin/activate

pip install --upgrade pip wheel setuptools
pip install .
```

Oczekiwany koniec: `Successfully built CityFlow` oraz `Successfully installed CityFlow-0.1`.

---

## 6. Test importu

```bash
python -c "import cityflow, sys; print('CityFlow import OK; Python', sys.version)"
```

---

## 7. Szybka symulacja (10 kroków) na przykładzie z repo

Repo zawiera `examples/config.json`. Uruchom:

```bash
python - <<'PY'
import cityflow
eng = cityflow.Engine("/home/dev/app/examples/config.json", thread_num=1)
for _ in range(10):
    eng.next_step()
print("Sim OK using examples/config.json")
PY
```

Oczekiwany output: `Sim OK using examples/config.json`.

> Uwaga: Jeśli używasz własnego `config.json`, upewnij się, że pole `dir` wskazuje katalog z plikami, a `roadnetFile` i `flowFile` są ścieżkami względnymi względem `dir`.

---

## 8. (Opcjonalnie) docker-compose dla wygody

`C:\Users\antek\Desktop\CityFlow\docker-compose.yml`:

```yaml
services:
  cityflow:
    image: cityflow:py310
    container_name: cityflow-dev
    user: root
    working_dir: /home/dev/app
    volumes:
      - //c/Users/antek/Desktop/CityFlow:/home/dev/app
    tty: true
    stdin_open: true
```

Obsługa:

```powershell
docker compose up -d
docker exec -it cityflow-dev bash
docker compose down
```

---

## 9. Najczęstsze problemy i szybkie poprawki

- `invalid reference format` przy `docker run -v`: użyj `//c/...` lub `/host_mnt/c/...` zamiast `/mnt/c/...`.
- `Permission denied` przy `python3 -m venv .venv`: uruchom kontener z `-u root`.
- `fatal error: Python.h: No such file or directory`: doinstaluj `python3-dev` (już ujęte w `Dockerfile.py310`).
- `cannot open roadnet file / load config failed`: sprawdź `dir` w `config.json`, użyj ścieżek względnych w `roadnetFile` i `flowFile`, zweryfikuj `ls -la /home/dev/app/examples` lub `python -m json.tool <config>`.

---

## 10. Co dalej

W kontenerze możesz doinstalować dodatkowe biblioteki LLM/RL:

```bash
pip install numpy pandas jupyterlab
# przykładowo pod LLM:
# pip install transformers accelerate
```

Chcesz szkielet `agents/`, `configs/`, `runs/` oraz minimalny `run_agent.py` (heurystyka → później LLM)? Daj znać — przygotujemy komplet z krótkim README opisującym pracę z `cityflow.Engine`.

---
### 🧾 Licencja i pochodzenie
Niniejsze repozytorium jest oparte na projekcie [CityFlow](https://github.com/cityflow-project/CityFlow),
który jest dostępny na licencji **Apache License 2.0**.  
Niniejsza wersja zawiera dodatkowe pliki i modyfikacje:
- zaktualizowany Dockerfile (Ubuntu 22.04 + Python 3.10)
- README z instrukcją uruchomienia w kontenerze
- foldery `agents/`, `configs/`, `runs/` dla eksperymentów z LLM
---