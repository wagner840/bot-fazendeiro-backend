
import pytest
from database import get_produtos_referencia
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)

@pytest.mark.asyncio
async def test_get_produtos_referencia_isolated(mock_supabase, mock_config):
    """
    Test if get_produtos_referencia correctly applies the isolation filter.
    """
    # Arrange
    guild_id = "123456"
    tipo_empresa_id = 1
    
    expected_data = [{'id': 1, 'nome': 'Jornal', 'guild_id': None}, {'id': 2, 'nome': 'Jornal Local', 'guild_id': '123456'}]
    
    # IMPORTANT: supabase.table() returns the query_builder.
    # So we must set the return value on that object's execute method.
    query_builder = mock_supabase.table.return_value
    query_builder.execute.return_value.data = expected_data

    # Act
    result = await get_produtos_referencia(tipo_empresa_id, guild_id)

    # Assert
    assert result == expected_data
    
    # Verify chain calls
    mock_supabase.table.assert_called_with('produtos_referencia')
    
    # Verify logic branching
    # The .or_ method is called on the query_builder
    query_builder.or_.assert_called()
    args, _ = query_builder.or_.call_args
    assert "guild_id.is.null" in args[0]
    assert f"guild_id.eq.{guild_id}" in args[0]

@pytest.mark.asyncio
async def test_get_produtos_referencia_global_only(mock_supabase, mock_config):
    """
    Test if get_produtos_referencia applies only global filter when guild_id is None.
    """
    # Arrange
    guild_id = None
    tipo_empresa_id = 1
    
    query_builder = mock_supabase.table.return_value
    query_builder.execute.return_value.data = []

    # Act
    await get_produtos_referencia(tipo_empresa_id, guild_id)
    query_builder.is_.assert_called_with('guild_id', 'null')
    # Ensure .or_ was NOT called
    query_builder.or_.assert_not_called()
