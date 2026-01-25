
import pytest
from database import atualizar_canal_funcionario, criar_produto_referencia_custom
import logging

@pytest.mark.asyncio
async def test_atualizar_canal_funcionario(mock_supabase, mock_config):
    """
    Test updating the channel_id for a specific employee.
    """
    # Arrange
    func_id = 99
    channel_id = "999999999"
    
    # Act
    result = await atualizar_canal_funcionario(func_id, channel_id)

    # Assert
    assert result is True
    
    # Verify table selection
    mock_supabase.table.assert_called_with('funcionarios')
    
    # Verify query builder calls
    query_builder = mock_supabase.table.return_value
    query_builder.update.assert_called_with({'channel_id': channel_id})
    query_builder.eq.assert_called_with('id', func_id)
    query_builder.execute.assert_called()

@pytest.mark.asyncio
async def test_criar_produto_referencia_custom(mock_supabase, mock_config):
    """
    Test creating a custom product reference with guild_id.
    """
    # Arrange
    tipo_id = 1
    nome = "Jornal Exclusivo"
    codigo = "jor1"
    categoria = "Jornal"
    guild_id = "12345"
    
    # Mock return
    expected_return = {
        'id': 100,
        'nome': nome,
        'guild_id': guild_id
    }
    
    query_builder = mock_supabase.table.return_value
    query_builder.execute.return_value.data = [expected_return]
    
    # Act
    result = await criar_produto_referencia_custom(tipo_id, nome, codigo, categoria, guild_id)
    
    # Assert
    assert result == expected_return
    
    # Check insert content
    mock_supabase.table.assert_called_with('produtos_referencia')
    args, _ = query_builder.insert.call_args
    inserted_data = args[0]
    
    assert inserted_data['guild_id'] == guild_id
    assert inserted_data['nome'] == nome
    assert inserted_data['codigo'] == "jor1"
    
