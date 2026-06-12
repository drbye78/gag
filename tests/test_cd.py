"""
Tests for CD pipeline workflow.

Validates:
- Smoke test jobs exist for dev and prod
- Rollback mechanism is configured
- Health check endpoints are tested
- Job dependencies are correct
"""

from pathlib import Path

import pytest
import yaml

# Path to the CD workflow file
CD_WORKFLOW_PATH = Path(__file__).parent.parent / ".github" / "workflows" / "cd.yml"


def load_cd_workflow() -> dict:
    """Load and parse the CD workflow YAML file."""
    with open(CD_WORKFLOW_PATH, "r") as f:
        return yaml.safe_load(f)


@pytest.fixture
def cd_workflow():
    """Fixture to load CD workflow."""
    return load_cd_workflow()


class TestCDWorkflowStructure:
    """Test the overall structure of the CD workflow."""

    def test_workflow_has_name(self, cd_workflow):
        """Workflow should have a name."""
        assert "name" in cd_workflow
        assert cd_workflow["name"] == "CD"

    def test_workflow_has_jobs(self, cd_workflow):
        """Workflow should have jobs defined."""
        assert "jobs" in cd_workflow
        assert len(cd_workflow["jobs"]) > 0

    def test_workflow_has_build_job(self, cd_workflow):
        """Workflow should have a build job."""
        assert "build" in cd_workflow["jobs"]

    def test_workflow_has_deploy_dev_job(self, cd_workflow):
        """Workflow should have a deploy-dev job."""
        assert "deploy-dev" in cd_workflow["jobs"]

    def test_workflow_has_deploy_prod_job(self, cd_workflow):
        """Workflow should have a deploy-prod job."""
        assert "deploy-prod" in cd_workflow["jobs"]


class TestSmokeTestJobs:
    """Test smoke test job configuration."""

    def test_smoke_test_dev_exists(self, cd_workflow):
        """Smoke test job for dev should exist."""
        assert "smoke-test-dev" in cd_workflow["jobs"]

    def test_smoke_test_prod_exists(self, cd_workflow):
        """Smoke test job for prod should exist."""
        assert "smoke-test-prod" in cd_workflow["jobs"]

    def test_smoke_test_dev_depends_on_deploy(self, cd_workflow):
        """Smoke test dev should depend on build and deploy-dev."""
        job = cd_workflow["jobs"]["smoke-test-dev"]
        assert "needs" in job
        needs = job["needs"]
        assert "build" in needs
        assert "deploy-dev" in needs

    def test_smoke_test_prod_depends_on_deploy(self, cd_workflow):
        """Smoke test prod should depend on build and deploy-prod."""
        job = cd_workflow["jobs"]["smoke-test-prod"]
        assert "needs" in job
        needs = job["needs"]
        assert "build" in needs
        assert "deploy-prod" in needs

    def test_smoke_test_has_timeout(self, cd_workflow):
        """Smoke tests should have timeout set."""
        dev_job = cd_workflow["jobs"]["smoke-test-dev"]
        prod_job = cd_workflow["jobs"]["smoke-test-prod"]

        assert "timeout-minutes" in dev_job
        assert dev_job["timeout-minutes"] <= 5

        assert "timeout-minutes" in prod_job
        assert prod_job["timeout-minutes"] <= 5


class TestHealthCheckVerification:
    """Test health check verification in smoke tests."""

    def test_smoke_test_has_health_check_step(self, cd_workflow):
        """Smoke tests should have health check step."""
        dev_steps = cd_workflow["jobs"]["smoke-test-dev"]["steps"]
        prod_steps = cd_workflow["jobs"]["smoke-test-prod"]["steps"]

        dev_has_health = any("health" in step.get("name", "").lower() for step in dev_steps)
        prod_has_health = any("health" in step.get("name", "").lower() for step in prod_steps)

        assert dev_has_health, "Dev smoke test should have health check step"
        assert prod_has_health, "Prod smoke test should have health check step"

    def test_smoke_test_has_metrics_check_step(self, cd_workflow):
        """Smoke tests should have metrics check step."""
        dev_steps = cd_workflow["jobs"]["smoke-test-dev"]["steps"]
        prod_steps = cd_workflow["jobs"]["smoke-test-prod"]["steps"]

        dev_has_metrics = any("metrics" in step.get("name", "").lower() for step in dev_steps)
        prod_has_metrics = any("metrics" in step.get("name", "").lower() for step in prod_steps)

        assert dev_has_metrics, "Dev smoke test should have metrics check step"
        assert prod_has_metrics, "Prod smoke test should have metrics check step"

    def test_health_check_uses_curl(self, cd_workflow):
        """Health check should use curl to verify endpoint."""
        dev_job = cd_workflow["jobs"]["smoke-test-dev"]
        prod_job = cd_workflow["jobs"]["smoke-test-prod"]

        # Find health check steps
        for step in dev_job["steps"]:
            if "health" in step.get("name", "").lower():
                run = step.get("run", "")
                assert "curl" in run, "Health check should use curl"
                assert "/health" in run, "Health check should call /health endpoint"

        for step in prod_job["steps"]:
            if "health" in step.get("name", "").lower():
                run = step.get("run", "")
                assert "curl" in run, "Health check should use curl"
                assert "/health" in run, "Health check should call /health endpoint"

    def test_health_check_verifies_200_response(self, cd_workflow):
        """Health check should verify 200 response code."""
        dev_job = cd_workflow["jobs"]["smoke-test-dev"]

        for step in dev_job["steps"]:
            if "health" in step.get("name", "").lower():
                run = step.get("run", "")
                assert "200" in run, "Health check should verify 200 response"


class TestRollbackMechanism:
    """Test rollback mechanism configuration."""

    def test_smoke_test_has_rollback_step(self, cd_workflow):
        """Smoke tests should have rollback step on failure."""
        dev_job = cd_workflow["jobs"]["smoke-test-dev"]
        prod_job = cd_workflow["jobs"]["smoke-test-prod"]

        dev_has_rollback = any(
            "rollback" in step.get("name", "").lower() for step in dev_job["steps"]
        )
        prod_has_rollback = any(
            "rollback" in step.get("name", "").lower() for step in prod_job["steps"]
        )

        assert dev_has_rollback, "Dev smoke test should have rollback step"
        assert prod_has_rollback, "Prod smoke test should have rollback step"

    def test_rollback_runs_on_failure(self, cd_workflow):
        """Rollback should run on failure (if: failure())."""
        dev_job = cd_workflow["jobs"]["smoke-test-dev"]

        for step in dev_job["steps"]:
            if "rollback" in step.get("name", "").lower():
                assert "if" in step
                assert "failure()" in step["if"], "Rollback should run on failure"

    def test_rollback_uses_kubectl_rollout_undo(self, cd_workflow):
        """Rollback should use kubectl rollout undo."""
        dev_job = cd_workflow["jobs"]["smoke-test-dev"]

        for step in dev_job["steps"]:
            if "rollback" in step.get("name", "").lower():
                run = step.get("run", "")
                assert "kubectl rollout undo" in run, "Rollback should use kubectl rollout undo"

    def test_rollback_waits_for_completion(self, cd_workflow):
        """Rollback should wait for completion."""
        dev_job = cd_workflow["jobs"]["smoke-test-dev"]

        for step in dev_job["steps"]:
            if "rollback" in step.get("name", "").lower():
                run = step.get("run", "")
                assert "kubectl rollout status" in run, "Rollback should wait for completion"


class TestDeploymentConfiguration:
    """Test deployment job configuration."""

    def test_deploy_dev_uses_kubectl(self, cd_workflow):
        """Deploy dev should use kubectl."""
        job = cd_workflow["jobs"]["deploy-dev"]
        steps = job["steps"]

        has_kubectl = any("kubectl" in step.get("run", "") for step in steps if "run" in step)

        assert has_kubectl, "Deploy dev should use kubectl"

    def test_deploy_prod_uses_kubectl(self, cd_workflow):
        """Deploy prod should use kubectl."""
        job = cd_workflow["jobs"]["deploy-prod"]
        steps = job["steps"]

        has_kubectl = any("kubectl" in step.get("run", "") for step in steps if "run" in step)

        assert has_kubectl, "Deploy prod should use kubectl"

    def test_deploy_waits_for_rollout(self, cd_workflow):
        """Deploy should wait for rollout status."""
        dev_job = cd_workflow["jobs"]["deploy-dev"]

        has_rollout_status = any(
            "rollout status" in step.get("run", "") for step in dev_job["steps"] if "run" in step
        )

        assert has_rollout_status, "Deploy should wait for rollout status"


class TestBuildJob:
    """Test build job configuration."""

    def test_build_has_docker_buildx(self, cd_workflow):
        """Build should use Docker Buildx."""
        job = cd_workflow["jobs"]["build"]
        steps = job["steps"]

        has_buildx = any("docker/setup-buildx-action" in step.get("uses", "") for step in steps)

        assert has_buildx, "Build should use Docker Buildx"

    def test_build_has_login_to_registry(self, cd_workflow):
        """Build should login to container registry."""
        job = cd_workflow["jobs"]["build"]
        steps = job["steps"]

        has_login = any("docker/login-action" in step.get("uses", "") for step in steps)

        assert has_login, "Build should login to container registry"

    def test_build_has_image_tag_output(self, cd_workflow):
        """Build should output image-tag."""
        job = cd_workflow["jobs"]["build"]
        assert "outputs" in job
        assert "image-tag" in job["outputs"]


class TestEnvironmentConfiguration:
    """Test environment configuration."""

    def test_deploy_dev_has_dev_environment(self, cd_workflow):
        """Deploy dev should have development environment."""
        job = cd_workflow["jobs"]["deploy-dev"]
        assert "environment" in job
        assert job["environment"] == "development"

    def test_deploy_prod_has_prod_environment(self, cd_workflow):
        """Deploy prod should have production environment."""
        job = cd_workflow["jobs"]["deploy-prod"]
        assert "environment" in job
        assert job["environment"] == "production"

    def test_smoke_test_dev_has_dev_environment(self, cd_workflow):
        """Smoke test dev should have development environment."""
        job = cd_workflow["jobs"]["smoke-test-dev"]
        assert "environment" in job
        assert job["environment"] == "development"

    def test_smoke_test_prod_has_prod_environment(self, cd_workflow):
        """Smoke test prod should have production environment."""
        job = cd_workflow["jobs"]["smoke-test-prod"]
        assert "environment" in job
        assert job["environment"] == "production"


class TestConditionalExecution:
    """Test conditional execution based on branches/tags."""

    def test_deploy_dev_runs_on_develop_branch(self, cd_workflow):
        """Deploy dev should run on develop branch."""
        job = cd_workflow["jobs"]["deploy-dev"]
        assert "if" in job
        assert "refs/heads/develop" in job["if"]

    def test_deploy_prod_runs_on_tags(self, cd_workflow):
        """Deploy prod should run on version tags."""
        job = cd_workflow["jobs"]["deploy-prod"]
        assert "if" in job
        assert "refs/tags/v" in job["if"]

    def test_smoke_test_dev_runs_on_develop_branch(self, cd_workflow):
        """Smoke test dev should run on develop branch."""
        job = cd_workflow["jobs"]["smoke-test-dev"]
        assert "if" in job
        assert "refs/heads/develop" in job["if"]

    def test_smoke_test_prod_runs_on_tags(self, cd_workflow):
        """Smoke test prod should run on version tags."""
        job = cd_workflow["jobs"]["smoke-test-prod"]
        assert "if" in job
        assert "refs/tags/v" in job["if"]
