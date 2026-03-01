import unittest
from unittest.mock import MagicMock, patch
from prewarmer import Prewarmer

class TestPrewarmer(unittest.TestCase):
    @patch('docker.from_env')
    def setUp(self, mock_docker):
        self.mock_client = MagicMock()
        mock_docker.return_value = self.mock_client
        self.prewarmer = Prewarmer(languages={"c_std11": "rpl-runner-c"}, network="test_network")

    def test_prewarm_creates_and_pauses_containers(self):
        mock_container = MagicMock()
        self.mock_client.containers.create.return_value = mock_container
        
        self.prewarmer.prewarm()
        
        # Verify pool_size (default is 2) containers were created
        self.assertEqual(self.mock_client.containers.create.call_count, 2)
        self.assertEqual(mock_container.start.call_count, 2)
        self.assertEqual(mock_container.pause.call_count, 2)
        self.assertEqual(len(self.prewarmer.pool["c_std11"]), 2)

    def test_get_container_url_unpauses_and_refills(self):
        mock_container = MagicMock()
        mock_container.id = "test_id"
        self.prewarmer.pool["c_std11"] = [mock_container]
        
        # We need to mock prewarm to avoid recursive calls
        with patch.object(Prewarmer, 'prewarm') as mock_prewarm:
            url = self.prewarmer.get_container_url("c_std11")
            
            self.assertEqual(url, "http://test_id:8000")
            mock_container.unpause.assert_called_once()
            mock_prewarm.assert_called_once()
            self.assertEqual(len(self.prewarmer.pool["c_std11"]), 0)

    def test_cleanup_unpauses_stops_and_removes(self):
        mock_container = MagicMock()
        self.prewarmer.pool["c_std11"] = [mock_container]
        
        self.prewarmer.cleanup()
        
        mock_container.unpause.assert_called_once()
        mock_container.stop.assert_called_once()
        mock_container.remove.assert_called_once()
        self.assertEqual(len(self.prewarmer.pool["c_std11"]), 0)

if __name__ == "__main__":
    unittest.main()
