"""Downtown seeding logic."""
from .config import supabase, generate_code, BASE_DOWNTOWN_ID
from .data import DOWNTOWN_DATA


def seed_downtown():
    """Seed the Downtown base with types and products."""
    print("Seeding Downtown Base (ID: 1)...")

    # Ensure Base 1 exists
    res_base = supabase.table('bases_redm').select('*').eq('id', BASE_DOWNTOWN_ID).execute()
    if not res_base.data:
        print("Criando Base Downtown...")
        supabase.table('bases_redm').insert({
            'id': BASE_DOWNTOWN_ID,
            'nome': 'Downtown',
            'ativo': True
        }).execute()

    for cat_name, data in DOWNTOWN_DATA.items():
        print(f"Processing Category: {cat_name}...")

        # 1. Create or Get Type
        tipo_code = generate_code(cat_name)

        # Check if type exists
        res_type = supabase.table('tipos_empresa')\
            .select('id')\
            .eq('nome', cat_name)\
            .eq('base_redm_id', BASE_DOWNTOWN_ID)\
            .execute()

        if res_type.data:
            type_id = res_type.data[0]['id']
            print(f"  Type exists: {cat_name} (ID: {type_id})")
        else:
            new_type = {
                'base_redm_id': BASE_DOWNTOWN_ID,
                'codigo': tipo_code,
                'nome': cat_name,
                'descricao': f"Empresa de {cat_name}",
                'cor_hex': data['cor'],
                'icone': data['icone'],
                'ativo': True
            }
            res_new = supabase.table('tipos_empresa').insert(new_type).execute()
            type_id = res_new.data[0]['id']
            print(f"  Types created: {cat_name} (ID: {type_id})")

        # 2. Insert Products
        _seed_products(type_id, cat_name, data['produtos'])


def _seed_products(type_id: int, category_name: str, products: list):
    """Seed products for a given type."""
    for prod in products:
        prod_name = prod['nome']
        prod_code = generate_code(prod_name)

        # Check existence
        res_prod = supabase.table('produtos_referencia')\
            .select('id')\
            .eq('nome', prod_name)\
            .eq('tipo_empresa_id', type_id)\
            .execute()

        if not res_prod.data:
            new_prod = {
                'tipo_empresa_id': type_id,
                'codigo': prod_code,
                'nome': prod_name,
                'categoria': category_name,
                'preco_minimo': prod['min'],
                'preco_maximo': prod['max'],
                'unidade': 'un',
                'ativo': True
            }
            try:
                supabase.table('produtos_referencia').insert(new_prod).execute()
                print(f"    + Product: {prod_name}")
            except Exception as e:
                print(f"    ! Error inserting {prod_name}: {e}")
