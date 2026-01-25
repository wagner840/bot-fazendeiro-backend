
import sys
import os
import json
import re

# Add root directory to path to allow imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config import supabase
from logging_config import logger

BASE_VALIRIA_ID = 2

# Raw data from user
VALIRIA_DATA = {
  "servidor": "Valiria Roleplay",
  "data_tabela": "Janeiro de 2026",
  "categorias": {
    "Fazendas": [
      { "produto": "Caixa de Milho - Safra atual", "min": 2.25, "max": 2.34 },
      { "produto": "Açúcar", "min": 0.40, "max": 0.43 },
      { "produto": "Amido de Milho", "min": 0.43, "max": 0.78 },
      { "produto": "Caixa de Ovos", "min": 9.00, "max": 9.90 },
      { "produto": "Cera de Abelha", "min": 0.32, "max": 0.36 },
      { "produto": "Cerveja de Trigo", "min": 0.54, "max": 0.58 },
      { "produto": "Ervas Finas", "min": 1.44, "max": 1.51 },
      { "produto": "Farinha de Trigo", "min": 0.50, "max": 0.54 },
      { "produto": "Garrafa de Álcool", "min": 0.40, "max": 0.43 },
      { "produto": "Garrafa de Leite Integral", "min": 0.40, "max": 0.43 },
      { "produto": "Levedura", "min": 0.32, "max": 0.58 },
      { "produto": "Licor de Café", "min": 0.54, "max": 0.58 },
      { "produto": "Mel", "min": 0.29, "max": 0.36 },
      { "produto": "Melado de Cana", "min": 0.40, "max": 0.43 },
      { "produto": "Óleo de Milho", "min": 0.47, "max": 0.50 },
      { "produto": "Ovos", "min": 0.09, "max": 0.11 },
      { "produto": "Pó de Café", "min": 0.36, "max": 0.40 },
      { "produto": "Polpa de Amora", "min": 0.50, "max": 0.58 },
      { "produto": "Polpa de Laranja", "min": 0.50, "max": 0.58 },
      { "produto": "Polpa de Morango", "min": 0.50, "max": 0.58 },
      { "produto": "Pólvora", "min": 0.25, "max": 0.29 },
      { "produto": "Própolis", "min": 0.29, "max": 0.32 },
      { "produto": "Vasilhame de Leite", "min": 0.12, "max": "Fixo" },
      { "produto": "Qualquer Plantação", "min": 0.09, "max": "S/definição" },
      { "produto": "Caixa de Amora - Safra", "min": "Inativo", "max": "Inativo" },
      { "produto": "Caixa de Tomate - Safra", "min": "Inativo", "max": "Inativo" },
      { "produto": "Saca de Café - Safra", "min": "Inativo", "max": "Inativo" },
      { "produto": "Saca Groselha Dourada - Safra", "min": "Inativo", "max": "Inativo" }
    ],
    "Armarias": [
      { "produto": "Carabina de repetição Stencer", "min": 59.4, "max": 68.31 },
      { "produto": "Escopeta de cano duplo", "min": 63.8, "max": 73.37 },
      { "produto": "Evans de Repetição", "min": 85.8, "max": 98.67 },
      { "produto": "Lancaster (Winchester) de Repetição", "min": 82.5, "max": 94.88 },
      { "produto": "Litchfield (Henry) de Repetição", "min": 72.6, "max": 82.49 },
      { "produto": "Munição Anti-praga", "min": 0.18, "max": 0.21 },
      { "produto": "Munição de Pistola Expressa", "min": 0.46, "max": 0.53 },
      { "produto": "Munição de Pistola Normal", "min": 0.26, "max": 0.4 },
      { "produto": "Munição de Repetidora Expressa", "min": 0.4, "max": 0.46 },
      { "produto": "Munição de Repetidora Normal", "min": 0.26, "max": 0.37 },
      { "produto": "Munição de Revólver Expressa", "min": 0.4, "max": 0.46 },
      { "produto": "Munição de Revolver Normal", "min": 0.26, "max": 0.37 },
      { "produto": "Munição de Rifle elefante", "min": 0.43, "max": 0.53 },
      { "produto": "Munição de Rifle Expressa", "min": 0.63, "max": 0.7 },
      { "produto": "Munição de Rifle Normal", "min": 0.53, "max": 0.59 },
      { "produto": "Munição de Shotgun Normal", "min": 0.4, "max": 0.56 },
      { "produto": "Pano de Limpeza de Arma", "min": 39.6, "max": None },
      { "produto": "Personalização de ARMA", "min": None, "max": "20% do Custo Final" },
      { "produto": "Pistola M1899", "min": 79.2, "max": 92.4 },
      { "produto": "Pistola Mauser", "min": 59.4, "max": 72.6 },
      { "produto": "Pistola Volcanic", "min": 49.5, "max": 66.0 },
      { "produto": "Revólver (Cattleman) de Vaqueiro", "min": 33.0, "max": 46.2 },
      { "produto": "Revólver de Ação Dupla", "min": 39.6, "max": 52.8 },
      { "produto": "Revólver LeMat", "min": 82.5, "max": 95.7 },
      { "produto": "Revolver Schofield", "min": 42.9, "max": 52.8 },
      { "produto": "Rifle de Ferrolho", "min": 105.6, "max": 118.8 },
      { "produto": "Rifle Springfield", "min": 66.0, "max": 79.2 }
    ],
    "Ferrarias": [
      { "produto": "Capsula de Munição", "min": 0.86, "max": 0.94 },
      { "produto": "Cutelo", "min": 3.12, "max": 3.12 },
      { "produto": "Faca Comum", "min": 7.8, "max": 11.7 },
      { "produto": "Faca de Arremesso", "min": 11.7, "max": 15.6 },
      { "produto": "Lingote de Aço", "min": 3.67, "max": 3.74 },
      { "produto": "Lingote de Cobre", "min": 3.35, "max": 3.43 },
      { "produto": "Lingote de Ferro", "min": 2.57, "max": 2.65 },
      { "produto": "Lingote de Ouro", "min": 3.98, "max": 4.06 },
      { "produto": "Lingote de Prata", "min": 3.04, "max": 3.12 },
      { "produto": "Machado Avançado", "min": 11.7, "max": 15.6 },
      { "produto": "Moedor", "min": 0.59, "max": 0.62 },
      { "produto": "Picareta Avançada", "min": 11.7, "max": 15.6 },
      { "produto": "Prego", "min": 0.55, "max": 0.62 },
      { "produto": "Rastelo", "min": 2.34, "max": 3.12 },
      { "produto": "Seringa de Vidro", "min": 1.17, "max": 1.4 }
    ],
    "Artesanato": [
      { "produto": "Balde Vazio", "min": 0.5, "max": 0.66 },
      { "produto": "Bolsa", "min": 0.5, "max": 0.66 },
      { "produto": "Caixa de Madeira", "min": 0.5, "max": 0.53 },
      { "produto": "Câmera", "min": 33.0, "max": 39.6 },
      { "produto": "Cantil", "min": 1.98, "max": 2.64 },
      { "produto": "Coador de Café", "min": 0.83, "max": 0.86 },
      { "produto": "Frasco Vazio", "min": 0.53, "max": 0.55 },
      { "produto": "Garrafa de Vidro", "min": 0.44, "max": 0.46 },
      { "produto": "Linha de Algodão", "min": 0.37, "max": 0.4 },
      { "produto": "Mapa de Bolso", "min": 7.8, "max": 11.7 },
      { "produto": "Pigmento", "min": 0.23, "max": 0.26 },
      { "produto": "Sacas", "min": 0.46, "max": 0.53 },
      { "produto": "Vara de Pesca", "min": 2.97, "max": 2.97 },
      { "produto": "Vela", "min": 2.64, "max": 3.3 },
      { "produto": "Verniz", "min": 0.76, "max": 0.79 }
    ],
    "Alimentos": [
      { "produto": "Comida", "min": 0.6, "max": 0.95 },
      { "produto": "Bebidas", "min": 0.6, "max": 0.95 }
    ],
    "Ateliê": [
      { "produto": "Manequim", "min": None, "max": 72.0 },
      { "produto": "Peça de Roupa", "min": 18.0, "max": 24.0 },
      { "produto": "Pomada Para Cabelo", "min": 6.0, "max": 6.0 },
      { "produto": "Tecido de Algodão", "min": 6.0, "max": 7.2 }
    ],
    "Gráfica": [
      { "produto": "Celulose", "min": 0.08, "max": 0.1 },
      { "produto": "Diagrama de Munição", "min": 0.26, "max": 0.33 },
      { "produto": "Diagrama de Pistola", "min": 0.3, "max": 0.37 },
      { "produto": "Diagrama de Revolver", "min": 0.23, "max": 0.3 },
      { "produto": "Diagrama de Repetidora", "min": 0.56, "max": 0.63 },
      { "produto": "Diagrama de Rifle", "min": 0.92, "max": 0.99 },
      { "produto": "Diagrama de Shotgun", "min": 0.66, "max": 0.73 },
      { "produto": "Manual de Cruza", "min": 60.0, "max": 90.0 }
    ],
    "Mineradora": [
      { "produto": "Caixa Carvão Mineral Bruto", "min": 0.66, "max": 0.69 },
      { "produto": "Carvão Mineral Bruto", "min": 0.15, "max": 0.18 },
      { "produto": "Pepita de Chumbo", "min": 0.12, "max": 0.15 },
      { "produto": "Pepita de Cobre", "min": 0.54, "max": 0.57 },
      { "produto": "Pepita de Ferro", "min": 0.6, "max": 0.66 },
      { "produto": "Pepita de Ouro", "min": 0.69, "max": 0.72 },
      { "produto": "Pepita de Prata", "min": 0.66, "max": 0.69 },
      { "produto": "Pepita de Quartzo", "min": 0.3, "max": 0.33 },
      { "produto": "Qualquer Mineração", "min": 0.08, "max": "S/Desfinição" }
    ],
    "Tabacaria": [
      { "produto": "Caixa de Cigarro", "min": 2.16, "max": 2.5 },
      { "produto": "Charuto", "min": 1.08, "max": 1.3 },
      { "produto": "Goma de Mascar", "min": 1.44, "max": 1.5 }
    ],
    "Jornal": [
      { "produto": "Cartão de Visita", "min": 0.9, "max": 1.2 },
      { "produto": "Poster", "min": 4.2, "max": 5.4 },
      { "produto": "Revista", "min": 6.0, "max": 7.2 },
      { "produto": "Seda", "min": 0.6, "max": 0.9 },
      { "produto": "Valor da Divulgação", "min": 60.0, "max": "A Combinar" },
      { "produto": "Valor do Jornal", "min": 1.0, "max": 1.2 }
    ],
    "Estabulos": [
      { "produto": "Escova para Cavalos", "min": 6.0, "max": 9.0 },
      { "produto": "Estimulante de Cavalo", "min": 1.2, "max": 1.5 },
      { "produto": "Estimulante de Cruza", "min": 1800.0, "max": 2700.0 },
      { "produto": "Potros/Cavalos", "min": 4200.0, "max": 4200.0 },
      { "produto": "Reanimador de Cavalo", "min": 9.0, "max": 10.8 },
      { "produto": "Tônico de Cura para Cavalos", "min": 1.8, "max": 2.1 },
      { "produto": "Treinamento Cavalo", "min": 120.0, "max": 180.0 }
    ],
    "Madeireira": [
      { "produto": "Carvão Vegetal", "min": 0.31, "max": 0.35 },
      { "produto": "Fibra", "min": 0.31, "max": 0.35 },
      { "produto": "Madeira Cilindrica", "min": 0.47, "max": 0.55 },
      { "produto": "Resina", "min": 0.2, "max": 0.23 },
      { "produto": "Seiva de Árvore", "min": 0.08, "max": 0.12 },
      { "produto": "Tábua de Madeira", "min": 0.43, "max": 0.51 },
      { "produto": "Tronco de Madeira", "min": 0.04, "max": 0.06 },
      { "produto": "Qualquer Extração", "min": 0.07, "max": "S/Definição" }
    ],
    "Indígenas": [
      { "produto": "Arco", "min": 21.0, "max": 30.0 },
      { "produto": "Essência de Fertilidade", "min": 240.0, "max": 360.0 },
      { "produto": "Flechas", "min": 1.5, "max": 2.1 },
      { "produto": "Fogueira", "min": 9.9, "max": 13.2 },
      { "produto": "Laço Reforçado", "min": 15.0, "max": 18.0 },
      { "produto": "Pássaros", "min": 600.0, "max": 1200.0 },
      { "produto": "Tocha", "min": 21.3, "max": 27.3 },
      { "produto": "Tomahawk", "min": 9.9, "max": 16.5 }
    ],
    "Médicos": [
      { "produto": "Bandagem", "min": None, "max": 1.55 },
      { "produto": "Seringa de Reanimação", "min": None, "max": 2.4 },
      { "produto": "Tônico de cura Potente", "min": None, "max": 1.0 },
      { "produto": "Tratamento médico", "min": 5.0, "max": 7.0 }
    ],
    "Perfumaria": [
      { "produto": "Loção de Groselha Dourada", "min": 2.8, "max": 3.22 },
      { "produto": "Loção Orquidea Aranha", "min": 12.0, "max": 15.0 },
      { "produto": "Loção Orquidea Borboleta", "min": 2.4, "max": 3.6 },
      { "produto": "Loção Orquidea Dama da Noite", "min": 6.0, "max": 9.0 },
      { "produto": "Loção Orquidea Estrela de Acuna", "min": 18.0, "max": 30.0 },
      { "produto": "Loção de Orquidea Rainha", "min": 2.2, "max": 3.54 },
      { "produto": "Óleo de Girassol", "min": 2.4, "max": 3.6 },
      { "produto": "Perfume", "min": 1.2, "max": 3.6 }
    ]
  }
}

def generate_code(name, prefix=None):
    clean = re.sub(r'[^a-zA-Z0-9]', '_', name.lower())
    clean = re.sub(r'_+', '_', clean).strip('_')
    if prefix:
        return f"{prefix}_{clean}"
    return clean[:50]

def seed_valiria():
    print("Seedando Banco de Dados - Base VALIRIA (ID: 2)...")
    
    # 1. Ensure Valiria Base exists (Should be done by migration, but safety check)
    # Ignored to rely on schema migration
    
    # 2. Map Icon/Colors from Downtown (Hardcoded map or simplified)
    CATEGORY_META = {
      "Fazendas": {"icone": "🌾", "cor": "#16a34a"},
      "Armarias": {"icone": "🔫", "cor": "#1f2937"},
      "Ferrarias": {"icone": "⚒️", "cor": "#475569"},
      "Artesanato": {"icone": "🧶", "cor": "#db2777"},
      "Alimentos": {"icone": "🍖", "cor": "#ea580c"},
      "Ateliê": {"icone": "🧵", "cor": "#7c3aed"},
      "Gráfica": {"icone": "📜", "cor": "#2563eb"},
      "Mineradora": {"icone": "⛏️", "cor": "#52525b"},
      "Tabacaria": {"icone": "🚬", "cor": "#92400e"},
      "Jornal": {"icone": "📰", "cor": "#4b5563"},
      "Estabulos": {"icone": "🐎", "cor": "#854d0e"},
      "Madeireira": {"icone": "🪓", "cor": "#78350f"},
      "Indígenas": {"icone": "🏹", "cor": "#059669"},
      "Médicos": {"icone": "⚕️", "cor": "#dc2626"},
      "Perfumaria": {"icone": "🌸", "cor": "#d946ef"}
    }

    # 3. Process Categories
    for cat_name, products in VALIRIA_DATA['categorias'].items():
        print(f"Processando Categoria: {cat_name}...")
        
        # Create Type
        meta = CATEGORY_META.get(cat_name, {"icone": "📦", "cor": "#cccccc"})
        
        # Check if type exists for Valiria
        res_type = supabase.table('tipos_empresa').select('id').eq('nome', cat_name).eq('base_redm_id', BASE_VALIRIA_ID).execute()
        
        if res_type.data:
            type_id = res_type.data[0]['id']
            print(f"  Tipo já existe: ID {type_id}")
        else:
            new_type = {
                "base_redm_id": BASE_VALIRIA_ID,
                "codigo": generate_code(cat_name) + "_vl",
                "nome": cat_name,
                "descricao": f"Empresa de {cat_name} (Valiria)",
                "cor_hex": meta['cor'],
                "icone": meta['icone'],
                "ativo": True
            }

            res_new = supabase.table('tipos_empresa').insert(new_type).execute()
            type_id = res_new.data[0]['id']
            print(f"  Novo tipo criado: ID {type_id}")
        
        # 4. Process Products
        for prod in products:
            prod_name = prod['produto']
            
            # Helper to parse min/max
            def parse_val(v):
                if v is None: return None
                if isinstance(v, (int, float)): return float(v)
                if isinstance(v, str):
                    # Handle special cases
                    v_lower = v.lower()
                    if 'fixo' in v_lower: return -1.0 # Flag for fixed price check
                    if 'inativo' in v_lower: return None
                    if 's/definição' in v_lower or 'defini' in v_lower: return None
                    if '%' in v: return None # Handle text descriptions
                    try:
                        return float(v)
                    except ValueError:
                        return None
                return None

            p_min = parse_val(prod['min'])
            p_max = parse_val(prod['max'])
            
            # Special Logic for "Fixo"
            if p_max == -1.0:
                p_max = p_min # Set max = min for fixed prices
            
            # Check if product exists
            res_prod = supabase.table('produtos_referencia')\
                .select('id')\
                .eq('nome', prod_name)\
                .eq('tipo_empresa_id', type_id)\
                .execute()
            
            if not res_prod.data:
                new_prod = {
                    "tipo_empresa_id": type_id,
                    "codigo": generate_code(prod_name),
                    "nome": prod_name,
                    "categoria": cat_name,
                    "preco_minimo": p_min,
                    "preco_maximo": p_max,
                    "unidade": "un",
                    "ativo": True
                }
                supabase.table('produtos_referencia').insert(new_prod).execute()
                print(f"    + Produto: {prod_name}")
            else:
                print(f"    . Prd existe: {prod_name}")

    print("Seed Completo!")

if __name__ == "__main__":
    seed_valiria()
