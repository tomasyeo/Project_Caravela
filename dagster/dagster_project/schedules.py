from dagster import ScheduleDefinition

# Reference job by name to avoid circular import with __init__.py.
# Dagster resolves "full_pipeline_job" from the Definitions object at load time.
full_pipeline_schedule = ScheduleDefinition(
    job_name="full_pipeline_job",
    cron_schedule="0 9 * * *",
    execution_timezone="Asia/Singapore",
)
