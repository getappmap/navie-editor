import unittest
from unittest.mock import Mock, patch, mock_open, call
from pathlib import Path
from navie.client import Client


class TestClient(unittest.TestCase):

    @patch("navie.client.os.system")
    @patch("navie.client.os.stat")
    @patch(
        "navie.client.open",
        new_callable=mock_open,
        read_data="Failed to complete: Connection error",
    )
    @patch("navie.client.time.sleep", return_value=None)
    def test_retry_successful_command(
        self, mock_sleep, mock_open, mock_stat, mock_system
    ):
        mock_system.return_value = 0
        mock_stat.return_value.st_size = 0
        result = Client.retry(3, 10, "echo 'Hello, World!'", Path("/tmp/log.txt"))
        self.assertEqual(result, 0)
        mock_sleep.assert_not_called()
        mock_stat.assert_called_once_with(Path("/tmp/log.txt"), follow_symlinks=True)
        mock_system.assert_called_once_with("echo 'Hello, World!'")
        mock_open.assert_called_with(Path("/tmp/log.txt"), "w")

    @patch("navie.client.os.system")
    @patch("navie.client.os.stat")
    @patch(
        "navie.client.open",
        new_callable=mock_open,
        read_data="Failed to complete: Connection error",
    )
    @patch("navie.client.time.sleep", return_value=None)
    def test_retry_with_retries(self, mock_sleep, mock_open, mock_stat, mock_system):
        mock_system.side_effect = [1, 1, 0]
        mock_stat.return_value.st_size = 0
        result = Client.retry(3, 10, "echo 'Hello, World!'", Path("/tmp/log.txt"))
        self.assertEqual(result, 0)
        self.assertEqual(mock_system.call_count, 3)
        self.assertEqual(mock_sleep.call_count, 2)

        expected_calls = [
            call(Path("/tmp/log.txt"), "w"),
            call().__enter__(),
            call().write("$ "),
            call().write("echo 'Hello, World!'"),
            call().write("\n\n"),
            call().__exit__(None, None, None),
            call(Path("/tmp/log.txt"), "r"),
            call().__enter__(),
            call().seek(0),
            call().read(),
            call().__exit__(None, None, None),
            call(Path("/tmp/log.txt"), "a"),
            call().__enter__(),
            call().write("$ "),
            call().write("echo 'Hello, World!'"),
            call().write("\n\n"),
            call().__exit__(None, None, None),
            call(Path("/tmp/log.txt"), "r"),
            call().__enter__(),
            call().seek(0),
            call().read(),
            call().__exit__(None, None, None),
            call(Path("/tmp/log.txt"), "a"),
            call().__enter__(),
            call().write("$ "),
            call().write("echo 'Hello, World!'"),
            call().write("\n\n"),
            call().__exit__(None, None, None),
        ]

        mock_open.assert_has_calls(expected_calls)

    @patch("navie.client.os.system")
    @patch("navie.client.os.stat")
    @patch(
        "navie.client.open",
        new_callable=mock_open,
        read_data="Failed to complete: Connection error",
    )
    @patch("navie.client.time.sleep", return_value=None)
    def test_retry_failure(
        self,
        mock_sleep: Mock,
        mock_open: Mock,
        mock_stat: Mock,
        mock_system: Mock,
    ):
        mock_system.return_value = 1
        mock_stat.return_value.st_size = 0

        with self.assertRaises(RuntimeError):
            Client.retry(3, 10, "echo 'Hello, World!'", Path("/tmp/log.txt"))
        self.assertEqual(mock_system.call_count, 3)
        self.assertEqual(mock_sleep.call_count, 2)
        assert call(Path("/tmp/log.txt"), "w") in mock_open.call_args_list
        assert call(Path("/tmp/log.txt"), "a") in mock_open.call_args_list

    # @patch("navie.client.os.system")
    # @patch("navie.client.os.stat")
    # @patch("navie.client.open", new_callable=mock_open)
    # @patch("navie.client.time.sleep", return_value=None)
    # def test_retry_log_file_growth(
    #     self, mock_sleep, mock_open_instance, mock_stat, mock_system
    # ):
    #     # Simulate the command failing twice and then succeeding
    #     mock_system.side_effect = [1, 1, 0]

    #     # Simulate the log file growing with each retry
    #     log_contents = [
    #         "$ echo 'Hello, World!'\n\nFailed to complete: Connection error",
    #         "$ echo 'Hello, World!'\n\nFailed to complete: Connection error\n$ echo 'Hello, World!'\n\nFailed to complete: Connection error",
    #         "$ echo 'Hello, World!'\n\nFailed to complete: Connection error\n$ echo 'Hello, World!'\n\nFailed to complete: Connection error\n$ echo 'Hello, World!'\n\n",
    #     ]

    #     mock_open_instance.return_value.read.side_effect = log_contents

    #     mock_stat.side_effect = [
    #         Mock(st_size=0),
    #         Mock(st_size=len(log_contents[0])),
    #         Mock(st_size=len(log_contents[1])),
    #     ]

    #     result = Client.retry(3, 10, "echo 'Hello, World!'", Path("/tmp/log.txt"))

    #     self.assertEqual(result, 0)
    #     self.assertEqual(mock_system.call_count, 3)
    #     self.assertEqual(mock_sleep.call_count, 2)

    #     # Check that stat was called correctly
    #     expected_stat_calls = [call(Path("/tmp/log.txt"), follow_symlinks=True)] * 3
    #     self.assertEqual(mock_stat.call_count, 3)
    #     mock_stat.assert_has_calls(expected_stat_calls)

    #     # Check that seek was called correctly
    #     expected_seek_calls = [call(len(log_contents[0])), call(len(log_contents[1]))]
    #     handle = mock_open()
    #     handle.seek.assert_has_calls(expected_seek_calls)


if __name__ == "__main__":
    unittest.main()
