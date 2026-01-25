
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config import supabase
from logging_config import logger

ID_SOURCE = 23 # Loja de Munições
ID_TARGET = 22 # Armaria

def migrate():
    print(f"Iniciando migração de ID {ID_SOURCE} para ID {ID_TARGET}...")

    # 1. Update Empresas
    print("Atualizando Empresas...")
    res_emp = supabase.table('empresas').update({'tipo_empresa_id': ID_TARGET}).eq('tipo_empresa_id', ID_SOURCE).execute()
    print(f"Empresas atualizadas: {len(res_emp.data)}")

    # 2. Update Produtos Referencia
    print("Atualizando Produtos de Referência...")
    res_prod = supabase.table('produtos_referencia').update({'tipo_empresa_id': ID_TARGET}).eq('tipo_empresa_id', ID_SOURCE).execute()
    print(f"Produtos atualizados: {len(res_prod.data)}")

    # 3. Delete Old Type
    print("Removendo tipo antigo...")
    res_del = supabase.table('tipos_empresa').delete().eq('id', ID_SOURCE).execute()
    print("Tipo antigo removido.")
    
    print("Migração concluída com sucesso.")

if __name__ == "__main__":
    migrate()
