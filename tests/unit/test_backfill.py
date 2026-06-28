#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
from unittest.mock import AsyncMock, MagicMock, patch
import os
import unittest
import json
from datetime import datetime, timedelta, date

# Mock aiohttp before importing client
mock_aiohttp = MagicMock()
sys.modules['aiohttp'] = mock_aiohttp
sys.modules['aiohttp.client'] = mock_aiohttp
mock_aiohttp.ClientSession.return_value = AsyncMock()

from globalomnium import Client, get_session, get_credentials
from globalomnium.go_types import HistoricalConsumption, ConsumptionForPeriod

FIXTURES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "fixtures"))


def read_fixture(fixture_name: str):
    with open(f"{FIXTURES_DIR}/{fixture_name}.bin", "rb") as fh:
        return fh.read()


class TestBackfill(unittest.IsolatedAsyncioTestCase):
    """Tests for get_historical_consumption_range and backfill_all_historical methods."""

    async def asyncSetUp(self):
        # Ensure credentials can be mocked or loaded
        try:
            u, p = get_credentials(credentials="credentials.json")
        except:
            u, p = "test_user", "test_pass"

        self.sess = await get_session()
        self.client = Client(self.sess, u, p, base_url="https://test.example.com/VirtualOffice")

    async def asyncTearDown(self):
        await self.sess.close()

    def _make_mock_consumption(self, start_dt: datetime, value: float) -> ConsumptionForPeriod:
        """Helper to create a mock ConsumptionForPeriod."""
        return ConsumptionForPeriod(
            start=start_dt,
            end=start_dt + timedelta(hours=1),
            value=value,
        )

    @patch.object(Client, 'is_logged', return_value=True)
    async def test_get_historical_consumption_range_single_chunk(self, _):
        """Test get_historical_consumption_range with a range within a single chunk."""
        with patch.object(
            self.client, '_get_historical_consumption', new_callable=AsyncMock
        ) as mock_get:
            # Create mock HistoricalConsumption for a single chunk
            mock_consumptions = [
                self._make_mock_consumption(datetime(2024, 5, 8, 0, 0), 0.011),
                self._make_mock_consumption(datetime(2024, 5, 8, 1, 0), 0.023),
            ]
            mock_get.return_value = HistoricalConsumption(
                consumptions=mock_consumptions,
                total=0.034,
            )

            start = datetime(2024, 5, 8)
            end = datetime(2024, 5, 8, 23, 59, 59)
            result = await self.client.get_historical_consumption_range(start, end, chunk_days=30)

            mock_get.assert_called_once()
            self.assertEqual(len(result.consumptions), 2)
            self.assertAlmostEqual(result.total, 0.034, places=3)

    @patch.object(Client, 'is_logged', return_value=True)
    async def test_get_historical_consumption_range_multiple_chunks(self, _):
        """Test get_historical_consumption_range with a range spanning multiple chunks."""
        call_count = 0

        async def mock_get_historical(start, end):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # First chunk: 2024-05-08 to 2024-05-30 (23 days)
                return HistoricalConsumption(
                    consumptions=[
                        self._make_mock_consumption(datetime(2024, 5, 8, 0, 0), 0.011),
                    ],
                    total=0.011,
                )
            else:
                # Second chunk: 2024-05-31 to 2024-06-10 (11 days)
                return HistoricalConsumption(
                    consumptions=[
                        self._make_mock_consumption(datetime(2024, 5, 31, 0, 0), 0.015),
                    ],
                    total=0.015,
                )

        with patch.object(
            self.client, '_get_historical_consumption', side_effect=mock_get_historical
        ) as mock_get:
            start = datetime(2024, 5, 8)
            end = datetime(2024, 6, 10, 23, 59, 59)
            result = await self.client.get_historical_consumption_range(start, end, chunk_days=30)

            # Should make 2 calls (34 days / 30 = 2 chunks)
            self.assertEqual(mock_get.call_count, 2)
            self.assertEqual(len(result.consumptions), 2)
            self.assertAlmostEqual(result.total, 0.026, places=3)
            # Verify consumptions are sorted by start time
            self.assertLess(result.consumptions[0].start, result.consumptions[1].start)

    @patch.object(Client, 'is_logged', return_value=True)
    async def test_get_historical_consumption_range_swapped_dates(self, _):
        """Test get_historical_consumption_range handles start > end by swapping."""
        with patch.object(
            self.client, '_get_historical_consumption', new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = HistoricalConsumption(
                consumptions=[],
                total=0.0,
            )

            start = datetime(2024, 5, 15)
            end = datetime(2024, 5, 8)
            result = await self.client.get_historical_consumption_range(start, end, chunk_days=30)

            # Should swap and still work
            mock_get.assert_called_once()
            args, _ = mock_get.call_args
            self.assertEqual(args[0], datetime(2024, 5, 8))
            # End date gets normalized to end of day
            self.assertEqual(args[1], datetime(2024, 5, 15, 23, 59, 59, 999999))

    @patch.object(Client, 'is_logged', return_value=True)
    async def test_get_historical_consumption_range_invalid_chunk_days(self, _):
        """Test get_historical_consumption_range raises ValueError for invalid chunk_days."""
        with self.assertRaises(ValueError):
            await self.client.get_historical_consumption_range(
                datetime(2024, 5, 8),
                datetime(2024, 5, 10),
                chunk_days=0,
            )

        with self.assertRaises(ValueError):
            await self.client.get_historical_consumption_range(
                datetime(2024, 5, 8),
                datetime(2024, 5, 10),
                chunk_days=-5,
            )

    @patch.object(Client, 'is_logged', return_value=True)
    async def test_get_historical_consumption_range_empty_results(self, _):
        """Test get_historical_consumption_range handles empty results from chunks."""
        with patch.object(
            self.client, '_get_historical_consumption', new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = HistoricalConsumption(
                consumptions=[],
                total=0.0,
            )

            start = datetime(2024, 5, 8)
            end = datetime(2024, 5, 15)
            result = await self.client.get_historical_consumption_range(start, end, chunk_days=30)

            self.assertEqual(len(result.consumptions), 0)
            self.assertEqual(result.total, 0.0)

    @patch.object(Client, 'is_logged', return_value=True)
    async def test_get_historical_consumption_range_exact_chunk_boundary(self, _):
        """Test get_historical_consumption_range with range exactly at chunk boundary."""
        call_count = 0

        async def mock_get_historical(start, end):
            nonlocal call_count
            call_count += 1
            return HistoricalConsumption(
                consumptions=[
                    self._make_mock_consumption(start, 0.01 * call_count),
                ],
                total=0.01 * call_count,
            )

        with patch.object(
            self.client, '_get_historical_consumption', side_effect=mock_get_historical
        ) as mock_get:
            # Exactly 30 days - should be 1 chunk
            start = datetime(2024, 5, 1)
            end = datetime(2024, 5, 30, 23, 59, 59)
            result = await self.client.get_historical_consumption_range(start, end, chunk_days=30)

            self.assertEqual(mock_get.call_count, 1)

            # 31 days - should be 2 chunks
            call_count = 0
            end = datetime(2024, 5, 31, 23, 59, 59)
            # Create a new mock for the second call to avoid accumulated call_count
            with patch.object(
                self.client, '_get_historical_consumption', side_effect=mock_get_historical
            ) as mock_get2:
                result = await self.client.get_historical_consumption_range(start, end, chunk_days=30)
                self.assertEqual(mock_get2.call_count, 2)

    @patch.object(Client, 'is_logged', return_value=True)
    async def test_backfill_all_historical_default_end_date(self, _):
        """Test backfill_all_historical uses today as default end_date."""
        with patch.object(
            self.client, 'get_historical_consumption_range', new_callable=AsyncMock
        ) as mock_range:
            mock_range.return_value = HistoricalConsumption(
                consumptions=[],
                total=0.0,
            )

            start_date = date(2024, 1, 1)
            result = await self.client.backfill_all_historical(start_date)

            mock_range.assert_called_once()
            args, kwargs = mock_range.call_args
            self.assertEqual(args[0].date(), start_date)
            self.assertEqual(args[1].date(), date.today())
            self.assertEqual(kwargs.get("chunk_days", 30), 30)

    @patch.object(Client, 'is_logged', return_value=True)
    async def test_backfill_all_historical_custom_end_date(self, _):
        """Test backfill_all_historical with custom end_date."""
        with patch.object(
            self.client, 'get_historical_consumption_range', new_callable=AsyncMock
        ) as mock_range:
            mock_range.return_value = HistoricalConsumption(
                consumptions=[],
                total=0.0,
            )

            start_date = date(2024, 1, 1)
            end_date = date(2024, 6, 30)
            result = await self.client.backfill_all_historical(start_date, end_date)

            mock_range.assert_called_once()
            args, _ = mock_range.call_args
            self.assertEqual(args[0].date(), start_date)
            self.assertEqual(args[1].date(), end_date)

    @patch.object(Client, 'is_logged', return_value=True)
    async def test_backfill_all_historical_invalid_start_after_end(self, _):
        """Test backfill_all_historical raises ValueError when start_date > end_date."""
        with self.assertRaises(ValueError):
            await self.client.backfill_all_historical(
                date(2024, 6, 30),
                date(2024, 1, 1),
            )

    @patch.object(Client, 'is_logged', return_value=True)
    async def test_backfill_all_historical_future_start_date(self, _):
        """Test backfill_all_historical raises ValueError when start_date is in the future."""
        future_date = date.today() + timedelta(days=1)
        with self.assertRaises(ValueError):
            await self.client.backfill_all_historical(future_date)

    @patch.object(Client, 'is_logged', return_value=True)
    async def test_backfill_all_historical_custom_chunk_days(self, _):
        """Test backfill_all_historical passes custom chunk_days."""
        with patch.object(
            self.client, 'get_historical_consumption_range', new_callable=AsyncMock
        ) as mock_range:
            mock_range.return_value = HistoricalConsumption(
                consumptions=[],
                total=0.0,
            )

            await self.client.backfill_all_historical(
                date(2024, 1, 1),
                date(2024, 6, 30),
                chunk_days=15,
            )

            mock_range.assert_called_once()
            _, kwargs = mock_range.call_args
            self.assertEqual(kwargs.get("chunk_days"), 15)

    @patch.object(Client, 'is_logged', return_value=True)
    async def test_backfill_all_historical_single_day(self, _):
        """Test backfill_all_historical with single day range."""
        with patch.object(
            self.client, 'get_historical_consumption_range', new_callable=AsyncMock
        ) as mock_range:
            mock_consumptions = [
                self._make_mock_consumption(datetime(2024, 5, 15, 0, 0), 0.05),
            ]
            mock_range.return_value = HistoricalConsumption(
                consumptions=mock_consumptions,
                total=0.05,
            )

            single_day = date(2024, 5, 15)
            result = await self.client.backfill_all_historical(single_day, single_day)

            self.assertEqual(len(result.consumptions), 1)
            self.assertAlmostEqual(result.total, 0.05, places=3)

    @patch.object(Client, 'is_logged', return_value=True)
    async def test_backfill_all_historical_returns_combined_data(self, _):
        """Test backfill_all_historical returns properly combined data from multiple chunks."""
        call_count = 0

        async def mock_get_historical(start, end):
            nonlocal call_count
            call_count += 1
            return HistoricalConsumption(
                consumptions=[
                    self._make_mock_consumption(start, 0.01 * call_count),
                ],
                total=0.01 * call_count,
            )

        with patch.object(
            self.client, '_get_historical_consumption', side_effect=mock_get_historical
        ) as mock_get:
            start_date = date(2024, 5, 1)
            end_date = date(2024, 6, 10)  # 41 days = 2 chunks with 30-day limit

            result = await self.client.backfill_all_historical(start_date, end_date, chunk_days=30)

            self.assertEqual(mock_get.call_count, 2)
            self.assertEqual(len(result.consumptions), 2)
            self.assertAlmostEqual(result.total, 0.03, places=3)
            # Verify sorted by start time
            self.assertLess(result.consumptions[0].start, result.consumptions[1].start)

    @patch.object(Client, 'is_logged', return_value=True)
    async def test_get_historical_consumption_range_preserves_order(self, _):
        """Test that results from multiple chunks are properly sorted by start time."""
        call_count = 0

        async def mock_get_historical(start, end):
            nonlocal call_count
            call_count += 1
            # Return data in reverse order to test sorting
            if call_count == 1:
                return HistoricalConsumption(
                    consumptions=[
                        self._make_mock_consumption(datetime(2024, 5, 15, 0, 0), 0.02),
                        self._make_mock_consumption(datetime(2024, 5, 10, 0, 0), 0.01),
                    ],
                    total=0.03,
                )
            else:
                return HistoricalConsumption(
                    consumptions=[
                        self._make_mock_consumption(datetime(2024, 6, 5, 0, 0), 0.04),
                        self._make_mock_consumption(datetime(2024, 6, 1, 0, 0), 0.03),
                    ],
                    total=0.07,
                )

        with patch.object(
            self.client, '_get_historical_consumption', side_effect=mock_get_historical
        ) as mock_get:
            start = datetime(2024, 5, 1)
            end = datetime(2024, 6, 10, 23, 59, 59)
            result = await self.client.get_historical_consumption_range(start, end, chunk_days=30)

            # Verify all consumptions are sorted by start time
            for i in range(len(result.consumptions) - 1):
                self.assertLessEqual(
                    result.consumptions[i].start,
                    result.consumptions[i + 1].start,
                    "Consumptions should be sorted by start time"
                )

    @patch.object(Client, 'is_logged', return_value=True)
    async def test_get_historical_consumption_range_total_calculation(self, _):
        """Test that total is correctly calculated as sum of chunk totals."""
        call_count = 0

        async def mock_get_historical(start, end):
            nonlocal call_count
            call_count += 1
            return HistoricalConsumption(
                consumptions=[
                    self._make_mock_consumption(start, 0.1),
                ],
                total=0.1 * call_count,  # 0.1, 0.2, 0.3...
            )

        with patch.object(
            self.client, '_get_historical_consumption', side_effect=mock_get_historical
        ) as mock_get:
            start = datetime(2024, 5, 1)
            end = datetime(2024, 6, 15, 23, 59, 59)  # ~46 days = 2 chunks
            result = await self.client.get_historical_consumption_range(start, end, chunk_days=30)

            # Total should be sum of chunk totals: 0.1 + 0.2 = 0.3
            self.assertAlmostEqual(result.total, 0.3, places=3)


if __name__ == "__main__":
    unittest.main()