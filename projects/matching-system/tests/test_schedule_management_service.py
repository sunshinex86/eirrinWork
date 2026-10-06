from src.utils.schedule_management_service import model_availability


class TestScheduleManagementService:
    """スケジュール管理サービスの業務要件テスト"""

    def test_project_start_date_bias_favors_on_time_start(self):
        early_candidate = {
            "available_from": "2026-08-01",
            "slots": [
                {"start": "2026-08-01T09:00:00", "end": "2026-08-01T18:00:00"}
            ],
        }
        on_time_candidate = {
            "available_from": "2026-09-01",
            "slots": [
                {"start": "2026-09-01T09:00:00", "end": "2026-09-01T18:00:00"}
            ],
        }
        job_window = {
            "project_start": "2026-09-01",
            "start": "2026-09-01T09:00:00",
            "end": "2026-09-01T18:00:00",
        }

        early_result = model_availability(early_candidate, job_window)
        on_time_result = model_availability(on_time_candidate, job_window)

        assert early_result["status"] == "match"
        assert on_time_result["status"] == "match"
        assert early_result["availability_score"] < on_time_result["availability_score"]
