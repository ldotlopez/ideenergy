import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
import aiohttp
from globalomnium.client import Client, InvalidData

@pytest.mark.asyncio
async def test_measure_logic():
    """
    Test the measure retrieval logic by mocking the network responses.
    This ensures the test is truly unit-based and doesn't depend on live credentials.
    """
    # Mock data for measure response
    mock_measure_data = {
        "table": [
            {"Lectura": "123,4", "Consumo": "0,5"}
        ]
    }

    # Setup mocks
    mock_session = AsyncMock()

    
    # We mock the request_bytes method of the Client because it's the core network handler
    # This allows us to simulate the API response without needing a real session
    with patch.object(Client, 'request_bytes', new_callable=AsyncMock) as mock_request:
        mock_request.return_value = b'{"table": [{"Lectura": "123,4", "Consumo": "0,5"}]}'
        
        client = Client(
            session=mock_session,
            username="test_user",
            password="test_pass",
            base_url="https://test.example.com/VirtualOffice"
        )
        client._login_ts = datetime.now() # Skip auth_required
        
        # Execute the method we want to test
        measure = await client.get_measure()
        
        # Assertions
        assert measure.accumulate == 123.4
        assert measure.instant == 0.5
        mock_request.assert_called_once()

@pytest.mark.asyncio
async def test_measure_error_handling():
    """
    Test how the client handles empty or malformed measure responses.
    """
    mock_session = AsyncMock()
    
    with patch.object(Client, 'request_bytes', new_callable=AsyncMock) as mock_request:
        # Simulate an empty table response
        mock_request.return_value = b'{"table": []}'
        
        client = Client(
            session=mock_session,
            username="test_user",
            password="test_pass",
            base_url="https://test.example.com/VirtualOffice"
        )
        client._login_ts = datetime.now() # Skip auth_required
        
        # This should probably return a Measure object with 0.0 values or raise a specific error
        # depending on the implementation. Based on current Client.get_measure:
        # it does: data['table'][0] -> this will raise IndexError.
        # Let's verify it raises InvalidData when table is empty.
        with pytest.raises(InvalidData):
            await client.get_measure()
