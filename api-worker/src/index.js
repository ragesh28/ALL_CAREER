const corsHeaders = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET,HEAD,POST,OPTIONS',
    'Access-Control-Max-Age': '86400',
    'Access-Control-Allow-Headers': '*',
    'Access-Control-Expose-Headers': 'X-Next-Cursor',
    'Content-Type': 'application/json'
};

const fields = 'role as title, company_name as company, location, job_posted_date as fetched_at, apply_link as url, apply_link as linkedin_url';
const routes = new Map([
    ['/api/all_jobs', ['all_jobs', fields + ', platform as source, search_keyword']],
    ['/api/big_company_jobs', ['big_company_jobs', fields]],
]);

export default {
    async fetch(request, env) {
        if (request.method === 'OPTIONS') return new Response(null, { headers: corsHeaders });

        const url = new URL(request.url);
        const route = routes.get(url.pathname);
        if (!route) return Response.json({ error: 'Route not found' }, { status: 404, headers: corsHeaders });

        const cursor = Number(url.searchParams.get('before') ?? Number.MAX_SAFE_INTEGER);
        const limit = Number(url.searchParams.get('limit') ?? 100);
        if (!Number.isSafeInteger(cursor) || cursor < 1 || !Number.isSafeInteger(limit) || limit < 1) {
            return Response.json({ error: 'Invalid page cursor or limit' }, { status: 400, headers: corsHeaders });
        }

        const pageSize = Math.min(limit, 500);
        const [table, columns] = route;
        try {
            const { results } = await env.DB.prepare(
                `SELECT id AS archive_cursor, ${columns} FROM ${table} WHERE id < ? ORDER BY id DESC LIMIT ?`
            ).bind(cursor, pageSize + 1).all();
            const page = results.slice(0, pageSize);
            const headers = new Headers(corsHeaders);
            if (results.length > pageSize) headers.set('X-Next-Cursor', String(page.at(-1).archive_cursor));
            return Response.json(page.map(({ archive_cursor, ...job }) => job), { headers });
        } catch {
            return Response.json({ error: 'Could not load jobs' }, { status: 500, headers: corsHeaders });
        }
    }
};
