
import pytest
from unittest.mock import AsyncMock, MagicMock
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

@pytest.fixture
def mock_supabase():
    """Mocks the Supabase async client."""
    # The final object that execute() is called on
    query_builder = MagicMock()

    # Result object returned by await execute()
    result_obj = MagicMock()
    result_obj.data = []

    # The execute function itself needs to be an AsyncMock (async) returning the result object
    execute_mock = AsyncMock(return_value=result_obj)
    query_builder.execute = execute_mock

    # The chainable methods on query_builder should return query_builder itself
    query_builder.table.return_value = query_builder
    query_builder.select.return_value = query_builder
    query_builder.eq.return_value = query_builder
    query_builder.order.return_value = query_builder
    query_builder.limit.return_value = query_builder
    query_builder.is_.return_value = query_builder
    query_builder.or_.return_value = query_builder
    query_builder.in_.return_value = query_builder
    query_builder.gt.return_value = query_builder
    query_builder.insert.return_value = query_builder
    query_builder.update.return_value = query_builder
    query_builder.delete.return_value = query_builder
    query_builder.upsert.return_value = query_builder
    query_builder.single.return_value = query_builder
    query_builder.rpc.return_value = query_builder

    # The client itself. When you call client.table(...), it starts the chain.
    client = MagicMock()
    client.table.return_value = query_builder
    client.rpc.return_value = query_builder

    return client

@pytest.fixture
def mock_config(mock_supabase):
    """Mocks the supabase client in all database submodules."""
    with pytest.MonkeyPatch.context() as m:
        # Patch supabase in all database submodules that import it
        m.setattr('config.supabase', mock_supabase)
        m.setattr('database.supabase', mock_supabase)
        submodules = [
            'database.servidor', 'database.usuario_frontend',
            'database.empresa', 'database.produto', 'database.funcionario',
            'database.estoque', 'database.transacao', 'database.encomenda',
            'database.assinatura', 'database.tester',
        ]
        for mod in submodules:
            try:
                m.setattr(f'{mod}.supabase', mock_supabase)
            except AttributeError:
                pass
        yield m
