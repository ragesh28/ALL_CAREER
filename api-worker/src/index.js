// A simple Cloudflare Worker to serve D1 Database over JSON API with proper CORS compatibility

const corsHeaders = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET,HEAD,POST,OPTIONS',
    'Access-Control-Max-Age': '86400',
    'Access-Control-Allow-Headers': '*',
    'Content-Type': 'application/json'
};

export default {
    async fetch(request, env) {
        if (request.method === "OPTIONS") {
            return new Response(null, { headers: corsHeaders });
        }

        const url = new URL(request.url);
        
        try {
            if (url.pathname === '/api/all_jobs') {
                const { results } = await env.DB.prepare(
                    "SELECT role as title, company_name as company, location, job_posted_date as fetched_at, apply_link as url, apply_link as linkedin_url, platform as source, search_keyword FROM all_jobs ORDER BY id DESC LIMIT 400000"
                ).all();
                
                return new Response(JSON.stringify(results), { 
                    headers: corsHeaders 
                });
            }
            
            if (url.pathname === '/api/big_company_jobs') {
                const { results } = await env.DB.prepare(
                    "SELECT role as title, company_name as company, location, job_posted_date as fetched_at, apply_link as url, apply_link as linkedin_url FROM big_company_jobs ORDER BY id DESC LIMIT 400000"
                ).all();
                
                return new Response(JSON.stringify(results), { 
                    headers: corsHeaders 
                });
            }

            return new Response(JSON.stringify({ error: "Route not found" }), { 
                status: 404, 
                headers: corsHeaders 
            });

        } catch (e) {
            return new Response(JSON.stringify({ error: e.message }), { 
                status: 500, 
                headers: corsHeaders 
            });
        }
    }
}
