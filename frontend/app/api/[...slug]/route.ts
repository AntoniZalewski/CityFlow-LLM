import { NextRequest } from "next/server";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://cityflow-api:8000";

type Ctx = { params: Promise<{ slug?: string[] }> };

async function proxy(request: NextRequest, ctx: Ctx) {
  const { slug = [] } = await ctx.params;
  const path = Array.isArray(slug) ? slug.join("/") : "";
  const targetUrl = new URL(`${API_BASE.replace(/\/$/, "")}/${path}`);

  request.nextUrl.searchParams.forEach((value, key) => {
    targetUrl.searchParams.set(key, value);
  });

  const body =
    request.method === "GET" || request.method === "HEAD" ? undefined : await request.text();

  const res = await fetch(targetUrl.toString(), {
    method: request.method,
    headers: { "content-type": request.headers.get("content-type") ?? "application/json" },
    body,
  });

  const text = await res.text();
  const safe = text?.length ? text : JSON.stringify({ ok: false, passthrough: true });

  return new Response(safe, {
    status: res.status,
    headers: { "content-type": res.headers.get("content-type") ?? "application/json" },
  });
}

export async function GET(req: NextRequest, ctx: Ctx) {
  return proxy(req, ctx);
}

export async function POST(req: NextRequest, ctx: Ctx) {
  return proxy(req, ctx);
}

export async function PUT(req: NextRequest, ctx: Ctx) {
  return proxy(req, ctx);
}

export async function PATCH(req: NextRequest, ctx: Ctx) {
  return proxy(req, ctx);
}

export async function DELETE(req: NextRequest, ctx: Ctx) {
  return proxy(req, ctx);
}
