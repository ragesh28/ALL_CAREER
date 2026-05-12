/**
 * Welcome to Cloudflare Workers! This is your first worker.
 *
 * - Run `npm run dev` in your terminal to start a development server
 * - Open a browser tab at http://localhost:8787/ to see your worker in action
 * - Run `npm run deploy` to publish your worker
 *
 * Bind resources to your worker in `wrangler.toml`. After adding bindings, a type definition for the
 * `Env` object can be regenerated with `npm run cf-typegen`.
 *
 * Learn more at https://developers.cloudflare.com/workers/
 */

export interface Env {
	DB: D1Database;
	JOBS_DB: D1Database;
}

export default {
	async fetch(request: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
		const url = new URL(request.url);
		
		// Handle CORS Preflight
		if (request.method === "OPTIONS") {
			return new Response(null, {
				headers: {
					"Access-Control-Allow-Origin": "*",
					"Access-Control-Allow-Methods": "GET, OPTIONS",
					"Access-Control-Allow-Headers": "Content-Type",
				}
			});
		}

		try {
			if (url.pathname === "/api/problems") {
				const { results } = await env.DB.prepare(`
					SELECT p.*
					FROM problems p 
					LIMIT 5000
				`).all();
				return new Response(JSON.stringify(results), { headers: { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" } });
			}

			if (url.pathname === "/api/all_problems") {
				const { results } = await env.DB.prepare(`
					SELECT 
					    p.id, p.title, p.url, p.difficulty, p.acceptance,
					    MAX(cp.frequency) as frequency,
					    GROUP_CONCAT(DISTINCT pt.topic) as topics_str
					FROM problems p
					LEFT JOIN company_problems cp ON p.id = cp.problem_id
					LEFT JOIN problem_topics pt ON p.id = pt.problem_id
					GROUP BY p.id
					LIMIT 5000
				`).all();
				
				return new Response(JSON.stringify(results), {
					headers: { 
						"Content-Type": "application/json",
						"Access-Control-Allow-Origin": "*" 
					}
				});
			}

			if (url.pathname === "/api/companies") {
				const { results } = await env.DB.prepare(
					"SELECT company_name as name, COUNT(problem_id) as count FROM company_problems GROUP BY company_name ORDER BY company_name ASC"
				).all();
				
				return new Response(JSON.stringify(results), {
					headers: { 
						"Content-Type": "application/json",
						"Access-Control-Allow-Origin": "*" 
					}
				});
			}


			if (url.pathname === "/api/company") {
				const company = url.searchParams.get("name");
				if (!company) {
					return new Response(JSON.stringify({error: "Missing company name parameter"}), { status: 400 });
				}
				
				const { results } = await env.DB.prepare(`
					SELECT p.*, cp.frequency 
					FROM problems p 
					JOIN company_problems cp ON p.id = cp.problem_id 
					WHERE LOWER(cp.company_name) = ?
					ORDER BY cp.frequency DESC
					LIMIT 1000
				`).bind(company.toLowerCase()).all();
				
				return new Response(JSON.stringify(results), {
					headers: { 
						"Content-Type": "application/json",
						"Access-Control-Allow-Origin": "*" 
					}
				});
			}

            if (url.pathname === "/api/topics") {
				const topic = url.searchParams.get("topic");
				if (!topic) {
					return new Response(JSON.stringify({error: "Missing topic parameter"}), { status: 400 });
				}
				
				const { results } = await env.DB.prepare(`
					SELECT p.*
					FROM problems p 
					JOIN problem_topics pt ON p.id = pt.problem_id 
					WHERE pt.topic = ?
					LIMIT 200
				`).bind(topic).all();
				
				return new Response(JSON.stringify(results), {
					headers: { 
						"Content-Type": "application/json",
						"Access-Control-Allow-Origin": "*" 
					}
				});
			}

			if (url.pathname === "/api/all_jobs") {
				const { results } = await env.JOBS_DB.prepare(
					"SELECT role as title, company_name as company, location, job_posted_date as fetched_at, apply_link as url, apply_link as linkedin_url, platform as source, search_keyword FROM all_jobs ORDER BY job_posted_date DESC LIMIT 200"
				).all();
				return new Response(JSON.stringify(results), { 
					headers: { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" } 
				});
			}

			if (url.pathname === "/api/big_company_jobs") {
				const { results } = await env.JOBS_DB.prepare(
					"SELECT role as title, company_name as company, location, job_posted_date as fetched_at, apply_link as url, apply_link as linkedin_url FROM big_company_jobs ORDER BY job_posted_date DESC LIMIT 200"
				).all();
				return new Response(JSON.stringify(results), { 
					headers: { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" } 
				});
			}

			return new Response("Not Found", { status: 404 });
			
		} catch (e: any) {
			return new Response(JSON.stringify({ error: e.message }), { 
				status: 500,
				headers: { "Access-Control-Allow-Origin": "*" }
			});
		}
	},
};
