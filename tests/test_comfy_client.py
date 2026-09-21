import os
import pytest
from unittest.mock import MagicMock, patch
from comfy_client import ComfyUIBatchClient

def test_get_video_files_invalid_path():
    client = ComfyUIBatchClient()
    files = client.get_video_files("invalid_non_existent_folder_path_xyz")
    assert files == []

def test_get_video_files_filtering(tmp_path):
    client = ComfyUIBatchClient()
    
    v1 = tmp_path / "video1.mp4"
    v2 = tmp_path / "video2.MOV"
    t1 = tmp_path / "text.txt"
    v1.write_bytes(b"dummy")
    v2.write_bytes(b"dummy")
    t1.write_bytes(b"dummy")

    files = client.get_video_files(str(tmp_path))
    assert len(files) == 2
    basenames = [os.path.basename(f) for f in files]
    assert "video1.mp4" in basenames
    assert "video2.MOV" in basenames
    assert "text.txt" not in basenames

def test_check_connection_success():
    client = ComfyUIBatchClient("127.0.0.1:8188")
    with patch("requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_get.return_value = mock_resp
        
        assert client.check_connection() is True
        mock_get.assert_called_once_with("http://127.0.0.1:8188/system_stats", timeout=3)

def test_run_batch_next_index_progression(tmp_path):
    client = ComfyUIBatchClient()
    
    v1 = tmp_path / "01.mp4"
    v2 = tmp_path / "02.mp4"
    v1.write_bytes(b"dummy")
    v2.write_bytes(b"dummy")

    with patch.object(client, "load_workflow") as mock_wf, \
         patch.object(client, "queue_prompt") as mock_queue, \
         patch.object(client, "wait_for_prompt_and_get_output") as mock_wait:
        
        mock_wf.return_value = {
            "422": {"inputs": {"strings": ""}},
            "424": {"inputs": {"value": 0}}
        }
        mock_queue.return_value = {"prompt_id": "test-prompt-id"}
        mock_wait.return_value = (True, "http://127.0.0.1:8188/view?filename=test.mp4")

        next_idx = client.run_batch(
            folder_path=str(tmp_path),
            start_index=0,
            batch_count=1
        )
        
        assert next_idx == 1
