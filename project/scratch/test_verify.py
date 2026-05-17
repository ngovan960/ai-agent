import asyncio
from uuid import uuid4
from services.orchestrator.services.verification_service import VerificationPipeline

async def main():
    print("Initializing VerificationPipeline...")
    pipeline = VerificationPipeline()
    task_id = uuid4()
    code_path = "/tmp/workspace/nonexistent"
    print(f"Running pipeline for task {task_id} on path {code_path}...")
    result = await pipeline.run_pipeline(task_id=task_id, code_path=code_path, mode="dev")
    print("Pipeline completed successfully!")
    print(f"Status: {result.status} | Score: {result.score} | Steps: {len(result.steps)}")
    for sr in result.steps:
        print(f"  Step: {sr.step_name} | Status: {sr.status} | Exit Code: {sr.exit_code}")

if __name__ == "__main__":
    asyncio.run(main())
