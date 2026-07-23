# Product Requirements Document (PRD)
## AI Career Assistant — v3 (Updated)

> **Change summary from v2:** Added database recommendation (DynamoDB); locked deployment choice to the simplest reliable path given a 2-day build/submit window and a $100 AWS credit balance; added a Credit & Cost Safety Checklist to guarantee no bank charges occur.
>
> **Change summary from v1:** Replaced AWS App Runner (closed to new customers as of April 30, 2026) with a free-tier-compatible deployment path; added cost controls, CORS, HTTPS, and error handling as explicit requirements; finalized LLM provider decision point; scoped session state for MVP.

---

### 1. Product Overview
The AI Career Assistant is a web-based chatbot designed to help users with career guidance, resume suggestions, and interview preparation using an AI language model.

### 2. Objective
Build and deploy a minimal viable AI-powered chatbot application on AWS **within free-tier / promotional-credit limits**, demonstrating full-stack development, LLM integration, and cloud deployment.

### 3. Target Users
Students, fresh graduates, and job seekers looking for career advice, resume help, and interview preparation.

### 4. Problem Statement
Many students lack access to personalized career guidance and struggle with resumes and interviews.

### 5. Solution
A chatbot that provides instant AI-generated career advice, resume tips, and interview questions.

### 6. Core Features (MVP)
- Chat interface for user queries
- AI-generated career guidance
- Resume bullet suggestions
- Interview question generation

### 7. User Flow
User opens app → types question → backend sends request to LLM → response displayed in chat.

### 8. Tech Stack
| Layer | Choice |
|---|---|
| Frontend | HTML, CSS, JavaScript |
| Backend | FastAPI (Python) |
| Database | **DynamoDB — see §8.2** |
| LLM API | **Decide before build starts — see §8.1** |
| Deployment | **See §11 (revised)** |

#### 8.1 LLM Provider Decision (new — was previously left open)
v1 listed "OpenAI or Claude" as an either/or. This needs to be locked before backend code is written, since SDK, env var naming, and per-token cost differ.

- **Recommendation for MVP:** pick one provider and stick with it. If cost predictability matters most for a free-trial project, compare current per-token pricing for both before deciding — don't default to whichever is more familiar.
- Whichever is chosen, store the key as an environment variable (e.g. `LLM_API_KEY`), never in source control.

#### 8.2 Database Decision (new)

**Recommendation: Amazon DynamoDB.**

| Option | Verdict |
|---|---|
| **DynamoDB** ✅ | Recommended. "Always Free" tier (25GB storage, 25 read/write capacity units) is a **permanent allowance separate from your $100 promotional credit** — using it doesn't burn down your credit balance. No VPC/networking setup required, which matters when the backend is a single EC2 instance and time is short. Setup via console takes minutes. |
| RDS (Postgres/MySQL) | Not recommended for this timeline. Requires VPC/security group configuration, draws from your $100 credit on a new account, and is overkill for the simple, non-relational data this app produces. |
| Local SQLite on the EC2 instance | Works technically but isn't durable — data is lost if the instance is stopped/replaced, and it doesn't demonstrate "cloud deployment," which is an explicit objective (§2). |

**Why the app needs a DB at all:** to persist chat interactions (query + AI response + timestamp) so the MVP can demonstrate real data persistence, not just a stateless passthrough to the LLM.

**Suggested table:**
- Table name: `ChatHistory`
- Partition key: `session_id` (String)
- Sort key: `timestamp` (String, ISO 8601)
- Attributes: `user_message`, `ai_response`, `feature_type` (career_advice / resume_tip / interview_question)

**Access pattern:** backend writes one item per chat exchange using `boto3`. Attach an **IAM role to the EC2 instance** (via an instance profile) with least-privilege DynamoDB write/read permissions — this avoids hardcoding AWS credentials on the box entirely, which is both more secure and less setup than managing access keys.

### 9. Functional Requirements
- Accept user input via chat
- Send request to backend API
- Backend securely calls LLM API
- Return AI-generated response
- **(New)** Backend validates and sanitizes user input before sending to the LLM (length limits, empty-message rejection)
- **(New)** Backend handles LLM API failures/timeouts gracefully and returns a user-facing error message instead of hanging or crashing

### 10. Non-Functional Requirements
- Responsive UI
- Secure API key handling using environment variables
- Low latency responses
- **(New) CORS:** backend must explicitly allow the frontend's origin; without this the chat UI will silently fail to get responses once frontend and backend are on different hosts/ports.
- **(New) HTTPS:** the public URL must serve over HTTPS. Neither a bare EC2 instance nor single-instance Elastic Beanstalk provides this by default — plan for either an ALB + ACM certificate, or a reverse proxy (e.g. Caddy/nginx with Let's Encrypt) on the instance.
- **(New) Cost control:** since the chatbot calls a metered, paid LLM API and will be publicly reachable, add:
  - A per-IP or per-session rate limit on the chat endpoint
  - A hard daily/monthly token or request cap with a kill-switch
  - An AWS Budget alarm (billing alert) configured on day one of the AWS account, not after deployment

### 11. Deployment Requirements (revised — locked for 2-day submission timeline)

**Problem with v1:** AWS App Runner, the originally specified target, **stopped accepting new customers on April 30, 2026.** A new AWS account cannot create an App Runner service today. AWS's official replacement is Amazon ECS Express Mode, but that runs on Fargate behind an Application Load Balancer — neither is free-tier eligible.

**Given the constraints (2 days to build + deploy, $100 total credit, must not risk a bank charge), the deployment choice prioritizes reliability and setup speed over squeezing out the absolute lowest possible cost.** A serverless Lambda + API Gateway backend (discussed earlier) is the cheapest possible long-term option, but introduces packaging/debugging risk (ASGI adapter, IAM permissions, cold starts) that isn't worth it under a hard 2-day deadline. It remains listed as a future option in §14.

**Locked path:**
- **Compute:** Single EC2 `t3.micro` instance (confirm the console shows the "Free tier eligible" tag at launch), Ubuntu or Amazon Linux.
- **App:** Docker container running FastAPI, serving both the API and the static frontend files from the same instance — one deployable unit, one thing to debug.
- **Database:** DynamoDB table, accessed via an IAM instance role (see §8.2) — no extra networking setup.
- **HTTPS:** If time allows, nginx/Caddy + Let's Encrypt in front of the app. If HTTPS setup risks blowing the deadline, plain HTTP over the EC2 public IP is an acceptable fallback for a submission demo — note this explicitly to whoever is grading/reviewing rather than leaving it unstated.
- **Public URL accessible** via the EC2 instance's public IP or an Elastic IP (attach one so the address doesn't change on restart — note: an Elastic IP is free *only* while attached to a running instance; an unattached one is billed, so don't allocate one and leave it idle).

**Realistic cost check for this plan over 2 days:** even in the worst case where none of it counts as "free tier" and everything draws from your $100 credit, a t3.micro instance running continuously for 48 hours costs roughly $0.50, and DynamoDB at MVP-demo traffic is effectively $0. This plan will not meaningfully dent a $100 balance.

### 11.1 Credit & Cost Safety Checklist (new — do these first, before writing any code)

These take under 10 minutes total and are what actually prevents a surprise bank charge — not the choice of service:

1. **Confirm you're on the "Free Plan," not "Paid Plan."** This was chosen at account signup. The Free Plan cuts off access when credit runs out or after 6 months rather than silently charging your card. Check under Billing → Account settings if unsure.
2. **Set an AWS Budget alert immediately**, before launching anything — e.g. alert at $5 and $20. AWS Budgets → Create budget → Cost budget. Free to set up.
3. **Launch only free-tier-eligible resources**: confirm the "Free tier eligible" badge in the EC2 console before picking an instance type; use DynamoDB (Always Free) rather than RDS.
4. **Avoid the common hidden-cost traps:** don't allocate an Elastic IP unless it's attached to a running instance; don't create a NAT Gateway (not needed for this architecture); stop or terminate the EC2 instance once you're done, don't leave it running indefinitely after submission.
5. **Terminate cleanup after submission/grading:** terminate the EC2 instance and delete the DynamoDB table once the project has been reviewed, so nothing keeps running (and potentially costing) afterward.

### 12. Success Metrics
- Application runs without errors
- Responses generated successfully
- Accessible via public AWS link
- **(New)** Stays within AWS free-tier/credit budget for the MVP demo period

### 13. Scope Boundaries for MVP (updated)
- **Single-turn chat with persisted logging** — each chat exchange is independent (no multi-turn context sent back to the LLM), but is now written to DynamoDB for the record. This is *storage*, not *memory*: the AI still doesn't "remember" prior messages within a conversation for MVP.
- No content moderation beyond basic input sanitization — acceptable for a low-traffic personal/demo project, but flag before wider release.

### 14. Future Scope
- Resume upload analysis
- Job matching system
- User authentication
- Multi-turn conversation memory (would use `session_id` + DynamoDB history already being logged as the foundation)
- Content moderation / guardrails for production use
- Migrate backend to Lambda + API Gateway for a genuinely zero-marginal-cost, always-on architecture once the 2-day deadline pressure is gone
