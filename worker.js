export default {
  async fetch(request) {
    const url = new URL(request.url);
    const target = url.searchParams.get("url");
    const ref = url.searchParams.get("ref") || new URL(target).origin + "/";

    if (!target) {
      return new Response("Missing ?url=", { status: 400 });
    }

    try {
      const upstream = await fetch(target, {
        headers: {
          "User-Agent": "Mozilla/5.0 (compatible; StreamProxy/1.0)",
          "Referer": ref,
          "Origin": new URL(ref).origin,
          Range: request.headers.get("Range") || "",
        },
      });

      return new Response(upstream.body, {
        status: upstream.status,
        headers: upstream.headers,
      });
    } catch (err) {
      return new Response("Proxy error: " + err.message, { status: 500 });
    }
  },
};
