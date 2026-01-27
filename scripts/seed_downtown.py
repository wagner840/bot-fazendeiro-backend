
import sys
import os
import re

# Add root directory to path to allow imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config import supabase
from logging_config import logger

BASE_DOWNTOWN_ID = 1

# Data extracted from "Tabela de Preços Downtown.txt"
DOWNTOWN_DATA = {
    "Alimentos": {
        "icone": "🍖", "cor": "#ef4444",
        "produtos": [
            {"nome": "Ensopado de Carne", "min": 1.20, "max": 1.50},
            {"nome": "Costela de Porco Assada", "min": 1.20, "max": 1.50},
            {"nome": "Carne Assada", "min": 1.20, "max": 1.50},
            {"nome": "Sopa de Legumes", "min": 1.20, "max": 1.50},
            {"nome": "Carne Seca", "min": 1.20, "max": 1.50},
            {"nome": "Peixe Assado", "min": 1.20, "max": 1.50},
            {"nome": "Batata Recheada", "min": 1.20, "max": 1.50},
            {"nome": "Tortilhas", "min": 1.20, "max": 1.50},
            {"nome": "Arroz Doce", "min": 1.20, "max": 1.50},
            {"nome": "Frango Frito", "min": 1.20, "max": 1.50},
            {"nome": "Frango Caipira", "min": 1.20, "max": 1.50},
            {"nome": "Chilli com Carne", "min": 1.20, "max": 1.50},
            {"nome": "Bife Acebolado", "min": 1.20, "max": 1.50},
            {"nome": "Refeição Cowboy", "min": 1.20, "max": 1.50},
            {"nome": "Feijoada", "min": 1.20, "max": 1.50},
            {"nome": "Arroz de Carreteiro", "min": 1.20, "max": 1.50},
            {"nome": "Sopa de Carne", "min": 1.20, "max": 1.50},
            {"nome": "Sopa de Lentilhas", "min": 1.20, "max": 1.50},
            {"nome": "Creme de Galinha", "min": 1.20, "max": 1.50},
            {"nome": "Sopa de Feijão", "min": 1.20, "max": 1.50},
            {"nome": "Arroz com Ovo", "min": 1.20, "max": 1.50},
            {"nome": "Cuscuz com Ovo", "min": 1.20, "max": 1.50},
            {"nome": "Buchada", "min": 1.20, "max": 1.50},
            {"nome": "Picanha com Queijo", "min": 1.20, "max": 1.50},
            {"nome": "Caldo de Costela", "min": 1.20, "max": 1.50},
            {"nome": "Torresmo", "min": 1.20, "max": 1.50},
            {"nome": "Kasseler Mit Sauerkraut", "min": 1.20, "max": 1.50},
            {"nome": "Hardtack", "min": 1.20, "max": 1.50},
            {"nome": "Porção de Peixe", "min": 1.20, "max": 1.50},
            {"nome": "Churrasco", "min": 1.20, "max": 1.50},
            {"nome": "Sapo de Chocolate", "min": 1.20, "max": 1.50},
            {"nome": "Churros Sinaloa", "min": 1.20, "max": 1.50},
            {"nome": "Geléia Pé de Bezerro", "min": 1.20, "max": 1.50},
            {"nome": "Fricassê", "min": 1.50, "max": 1.80},
            {"nome": "Salpicão", "min": 1.50, "max": 1.80},
            {"nome": "Arroz a Grega", "min": 1.50, "max": 1.80},
            {"nome": "Arroz com Passas", "min": 1.50, "max": 1.80},
            {"nome": "Lasanha de Carne", "min": 1.50, "max": 1.80},
            {"nome": "Batata Assada", "min": 1.50, "max": 1.80},
            {"nome": "Frango Assado", "min": 1.50, "max": 1.80},
            {"nome": "Lombo Apimentado", "min": 1.50, "max": 1.80},
            {"nome": "Javali com Batatas", "min": 1.50, "max": 1.80},
            {"nome": "Ramén", "min": 2.50, "max": 3.10},
            {"nome": "Mochi", "min": 2.60, "max": 3.10},
            {"nome": "Arroz Japonês", "min": 2.70, "max": 3.10},
            {"nome": "Espetinho de Pombinho", "min": 1.20, "max": 1.50},
            {"nome": "Pamonha", "min": 1.20, "max": 1.50},
            {"nome": "Espetinho de Perereca", "min": 1.20, "max": 1.50},
            {"nome": "Costela Bovina Assada", "min": 1.20, "max": 1.50},
            {"nome": "Coxinha", "min": 9.00, "max": 11.00},
        ]
    },
    "Bebidas": {
        "icone": "🍺", "cor": "#f59e0b",
        "produtos": [
            {"nome": "Suco de Uva", "min": 1.00, "max": 1.30},
            {"nome": "Suco de Amora", "min": 1.00, "max": 1.30},
            {"nome": "Suco de Morango", "min": 1.00, "max": 1.30},
            {"nome": "Limonada", "min": 1.00, "max": 1.30},
            {"nome": "Suco de Pêssego", "min": 1.00, "max": 1.30},
            {"nome": "Suco de Maçã", "min": 1.00, "max": 1.30},
            {"nome": "Suco de Framboesa Vermelha", "min": 1.00, "max": 1.30},
            {"nome": "Suco de Groselha Negra", "min": 1.00, "max": 1.30},
            {"nome": "Suco de Ameixa", "min": 1.00, "max": 1.30},
            {"nome": "Suco de Maracujá", "min": 1.00, "max": 1.30},
            {"nome": "Limonada com Hortelã", "min": 1.00, "max": 1.30},
            {"nome": "Hidromel sem Álcool", "min": 1.00, "max": 1.30},
            {"nome": "Suco Verde", "min": 1.00, "max": 1.30},
            {"nome": "Leite com Melado", "min": 1.00, "max": 1.30},
            {"nome": "Suco de Cenoura", "min": 1.00, "max": 1.30},
            {"nome": "Suco de Frutas Vermelhas", "min": 1.00, "max": 1.30},
            {"nome": "Leite Quente", "min": 1.00, "max": 1.30},
            {"nome": "Suco de Gengibre", "min": 1.00, "max": 1.30},
            {"nome": "Creme de Café", "min": 1.00, "max": 1.30},
            {"nome": "Batida de Framboesa", "min": 1.00, "max": 1.30},
            {"nome": "Guaraná", "min": 1.00, "max": 1.30},
            {"nome": "MilkShake de Morango", "min": 1.00, "max": 1.30},
            {"nome": "Pinga Temperada", "min": 1.00, "max": 1.30},
            {"nome": "Suco de Laranja Natural", "min": 1.00, "max": 1.30},
            {"nome": "Suco de Laranja com Cenoura", "min": 1.00, "max": 1.30},
            {"nome": "Conhaque", "min": 1.00, "max": 1.30},
            {"nome": "Caipirinha de Gengibre", "min": 1.00, "max": 1.30},
            {"nome": "Blood Mary", "min": 1.00, "max": 1.30},
            {"nome": "Beijo da Prima de 2º Grau", "min": 1.00, "max": 1.30},
            {"nome": "Tequila", "min": 1.00, "max": 1.30},
            {"nome": "Cerveja Amanteigada", "min": 1.00, "max": 1.30},
            {"nome": "Polissuco", "min": 1.00, "max": 1.30},
            {"nome": "Chimarrão", "min": 1.00, "max": 1.30},
            {"nome": "Tererê", "min": 1.00, "max": 1.30},
            {"nome": "Rum Naufragado", "min": 1.00, "max": 1.30},
            {"nome": "Suco de Corno", "min": 0.60, "max": 1.10},
            {"nome": "Star Books", "min": 0.90, "max": 1.35},
            {"nome": "Vinho", "min": 1.50, "max": 1.80},
            {"nome": "Espumante", "min": 1.50, "max": 1.80},
            {"nome": "Saquê", "min": 2.80, "max": 3.20},
            {"nome": "Piña Colada", "min": 1.00, "max": 1.30},
            {"nome": "Cerveja IPA", "min": 1.20, "max": 1.50},
            {"nome": "Champanhe", "min": 1.20, "max": 1.50},
            {"nome": "Suco de Limão", "min": 1.50, "max": 1.80},
            {"nome": "Grogue", "min": 1.50, "max": 1.80},
        ]
    },
    "Padaria": {
        "icone": "🥐", "cor": "#eab308",
        "produtos": [
            {"nome": "Pudim", "min": 0.95, "max": 1.15},
            {"nome": "Bolo de Chocolate", "min": 1.00, "max": 1.20},
            {"nome": "Pão com Manteiga", "min": 0.80, "max": 0.95},
            {"nome": "Donuts", "min": 1.05, "max": 1.20},
            {"nome": "Biscoito", "min": 0.90, "max": 1.05},
            {"nome": "Café", "min": 0.75, "max": 0.90},
            {"nome": "Vitamina de Banana", "min": 0.85, "max": 0.95},
            {"nome": "Chocolate Quente", "min": 0.90, "max": 1.00},
            {"nome": "Vitamina de Morango", "min": 0.85, "max": 0.95},
            {"nome": "Vitamina de Guaraná", "min": 0.85, "max": 0.95},
            {"nome": "Pão de Melado", "min": 1.20, "max": 1.50},
            {"nome": "Sonho de Creme", "min": 0.95, "max": 1.20},
            {"nome": "Croissant Doce", "min": 1.15, "max": 1.50},
            {"nome": "Cappuccino", "min": 0.90, "max": 1.20},
            {"nome": "Pesadelo de Doce de Leite", "min": 0.90, "max": 1.35},
            {"nome": "Morango do Amor", "min": 1.50, "max": 2.00},
            {"nome": "Suco de Morango", "min": 1.00, "max": 1.30},
            {"nome": "Torta de Morango", "min": 1.50, "max": 2.00},
            {"nome": "Chocotone", "min": 1.50, "max": 1.80},
            {"nome": "Panetone", "min": 1.50, "max": 1.80},
            {"nome": "Biscoito Natalino", "min": 1.50, "max": 1.80},
            {"nome": "Bengala de Natal", "min": 1.50, "max": 1.80},
            {"nome": "Coca Cola", "min": 1.50, "max": 1.80},
        ]
    },
    "Fazenda": {
        "icone": "🌾", "cor": "#22c55e",
        "produtos": [
            {"nome": "Plantações", "min": 0.13, "max": 0.19},
            {"nome": "Álcool Artesanal", "min": 0.36, "max": 0.52},
            {"nome": "Álcool Industrial", "min": 0.44, "max": 0.78},
            {"nome": "Cerveja de Trigo", "min": 0.41, "max": 0.63},
            {"nome": "Farinha de Trigo", "min": 0.20, "max": 0.30},
            {"nome": "Açúcar", "min": 0.14, "max": 0.21},
            {"nome": "Melado de Cana", "min": 0.17, "max": 0.26},
            {"nome": "Amido de Milho", "min": 0.20, "max": 0.31},
            {"nome": "Óleo de Milho", "min": 0.23, "max": 0.34},
            {"nome": "Licor de Café", "min": 0.62, "max": 0.79},
            {"nome": "Pó de Café", "min": 0.23, "max": 0.29},
            {"nome": "Molho de Tomate", "min": 0.24, "max": 0.39},
            {"nome": "Ketchup", "min": 0.27, "max": 0.42},
            {"nome": "Batata Palha", "min": 0.33, "max": 0.49},
            {"nome": "Amido de Batata", "min": 0.13, "max": 0.22},
            {"nome": "Arroz Branco", "min": 0.21, "max": 0.25},
            {"nome": "Farinha de Arroz", "min": 0.21, "max": 0.25},
            {"nome": "Fibra de Linho", "min": 0.17, "max": 0.25},
            {"nome": "Óleo de Linhaça", "min": 0.22, "max": 0.33},
            {"nome": "Fibra de Algodão", "min": 0.19, "max": 0.24},
            {"nome": "Celulose", "min": 0.14, "max": 0.21},
            {"nome": "Fumo", "min": 0.20, "max": 0.26},
            {"nome": "Tabaco Curado", "min": 0.24, "max": 0.31},
            {"nome": "Pó de Pimenta", "min": 0.19, "max": 0.24},
            {"nome": "Conserva de Pimenta", "min": 0.21, "max": 0.29},
            {"nome": "Creme de Leite", "min": 0.60, "max": 0.80},
            {"nome": "Cacau em Pó", "min": 0.20, "max": 0.30},
            {"nome": "Pólvora", "min": 0.30, "max": 0.50},
            {"nome": "Cascalho", "min": 0.18, "max": 0.22},
            {"nome": "Leite de Búfala", "min": 0.11, "max": 0.16},
            {"nome": "Couro de Búfalo", "min": 0.11, "max": 0.16},
            {"nome": "Lã de Ovelha", "min": 0.11, "max": 0.16},
            {"nome": "Ovos", "min": 0.11, "max": 0.16},
            {"nome": "Leite de Cabra", "min": 0.11, "max": 0.16},
            {"nome": "Leite de Ovelha", "min": 0.11, "max": 0.16},
            {"nome": "Leite de Vaca", "min": 0.11, "max": 0.16},
            {"nome": "Leite de Mula", "min": 0.11, "max": 0.16},
            {"nome": "Leite de Porca", "min": 0.11, "max": 0.16},
            {"nome": "Taurina", "min": 0.11, "max": 0.16},
            {"nome": "Favo de Mel", "min": 0.20, "max": 0.30},
            {"nome": "Couro de Mula", "min": 0.11, "max": 0.16},
            {"nome": "Crina de Galo", "min": 0.11, "max": 0.16},
            {"nome": "Carne de Porco", "min": 0.11, "max": 0.16},
            {"nome": "Buchada de Bode", "min": 0.11, "max": 0.16},
            # Sacas included here as generic farming
            {"nome": "Saca de Milho", "min": 40.00, "max": 60.00},
            {"nome": "Saca de Cenouras", "min": 40.00, "max": 60.00},
            {"nome": "Saca de Uvas", "min": 40.00, "max": 60.00},
            {"nome": "Saca de Maçã", "min": 40.00, "max": 60.00},
            {"nome": "Saca de Feijão", "min": 40.00, "max": 60.00},
            {"nome": "Saca de Arroz", "min": 40.00, "max": 60.00},
            {"nome": "Saca de Tomate", "min": 40.00, "max": 60.00},
        ]
    },
    "Açougue": {
        "icone": "🥩", "cor": "#dc2626",
        "produtos": [
            {"nome": "Picanha", "min": 0.75, "max": 1.13},
            {"nome": "Alcatra", "min": 0.65, "max": 0.95},
            {"nome": "Fraldinha", "min": 0.60, "max": 0.85},
            {"nome": "Costela", "min": 0.63, "max": 0.88},
            {"nome": "Filé Mignon", "min": 0.70, "max": 1.05},
            {"nome": "Acém", "min": 0.58, "max": 0.80},
            {"nome": "Maminha", "min": 0.63, "max": 0.90},
            {"nome": "Cupim", "min": 0.68, "max": 0.95},
            {"nome": "Carne Moída", "min": 0.50, "max": 0.70},
            {"nome": "Patinho", "min": 0.58, "max": 0.80},
            {"nome": "Coxa de Ave", "min": 0.43, "max": 0.55},
            {"nome": "Sobrecoxa de Ave", "min": 0.45, "max": 0.58},
            {"nome": "Peito de Ave", "min": 0.50, "max": 0.65},
            {"nome": "Asa de Ave", "min": 0.38, "max": 0.80},
            {"nome": "Moela", "min": 0.30, "max": 0.40},
            {"nome": "Fígado de Ave", "min": 0.30, "max": 0.40},
            {"nome": "Coração de Ave", "min": 0.38, "max": 0.53},
            {"nome": "Filé de Peixe", "min": 0.50, "max": 0.70},
            {"nome": "Posta de Peixe", "min": 0.45, "max": 0.60},
            {"nome": "Lombo de Peixe", "min": 0.48, "max": 0.63},
            {"nome": "Pele de Peixe", "min": 0.28, "max": 0.38},
            {"nome": "Peixe Defumado", "min": 0.63, "max": 0.75},
            {"nome": "Costela de Porco", "min": 0.60, "max": 0.85},
            {"nome": "Pernil de Porco", "min": 0.65, "max": 0.90},
            {"nome": "Lomba de Porco", "min": 0.80, "max": 1.00},
            {"nome": "Panceta", "min": 0.55, "max": 0.75},
            {"nome": "Carne de Cobra", "min": 0.80, "max": 1.00},
            {"nome": "Carne de Jacaré", "min": 0.80, "max": 1.13},
            {"nome": "Carne de Urso", "min": 1.25, "max": 1.55},
            {"nome": "Carne de Lobo", "min": 1.00, "max": 1.25},
            {"nome": "Carne de Iguana", "min": 0.88, "max": 1.13},
            {"nome": "Carne de Bisão", "min": 1.13, "max": 1.38},
            {"nome": "Carne Exótica", "min": 0.80, "max": 1.00},
            {"nome": "Mistura", "min": 0.69, "max": 0.95},
        ]
    },
    "Gráfica": {
        "icone": "📚", "cor": "#6366f1",
        "produtos": [
            {"nome": "Manual de Pistola", "min": 20.00, "max": 22.00},
            {"nome": "Manual de Repetidora", "min": 25.00, "max": 28.00},
            {"nome": "Manual de Rifle", "min": 20.00, "max": 22.00},
            {"nome": "Manual de Shotgun", "min": 25.00, "max": 27.00},
            {"nome": "Manual de Munições", "min": 2.00, "max": 4.00},
            {"nome": "Manual de Revolver", "min": 20.00, "max": 22.00},
            {"nome": "Manual da Cruza", "min": 200.00, "max": 300.00},
            {"nome": "Livro de Caldeiras Avançadas", "min": 500.00, "max": 800.00},
            {"nome": "Upgrade do Barco", "min": 500.00, "max": 800.00},
        ]
    },
    "Estábulo": {
        "icone": "🐴", "cor": "#a855f7",
        "produtos": [
            {"nome": "Treinamento de Cavalo (1 Vez)", "min": 45.00, "max": 55.00},
            {"nome": "Ferradura de Ouro", "min": 8.00, "max": 9.50},
            {"nome": "Ferradura de Ferro", "min": 5.00, "max": 6.50},
            {"nome": "Super Boost Equino", "min": 1.50, "max": 3.00},
            {"nome": "Revitalizador Equino", "min": 10.00, "max": 12.00},
            {"nome": "Escova Equina", "min": 1.00, "max": 1.50},
            {"nome": "Libid Gel Concentrado", "min": 1000.00, "max": 1200.00},
            {"nome": "Acessório para Cavalo", "min": 1.00, "max": 1.50},
            {"nome": "Doce Equino", "min": 1.00, "max": 1.20},
            {"nome": "Cupcake Equino", "min": 1.00, "max": 1.20},
            {"nome": "Remédio Equino", "min": 1.50, "max": 3.00},
        ]
    },
    "Artesanato": {
        "icone": "🧵", "cor": "#ec4899",
        "produtos": [
            {"nome": "Linha de Algodão", "min": 0.50, "max": 0.80},
            {"nome": "Garrafa de Vidro", "min": 1.00, "max": 1.50},
            {"nome": "Frasco de Vidro", "min": 0.80, "max": 1.20},
            {"nome": "Cápsula Plástica", "min": 0.30, "max": 0.50},
            {"nome": "Alça de Couro", "min": 0.80, "max": 1.20},
            {"nome": "Mochila 20 Kg", "min": 40.00, "max": 60.00},
            {"nome": "Embalagem", "min": 0.50, "max": 0.80},
            {"nome": "Coador", "min": 0.50, "max": 1.00},
            {"nome": "Vara de Pescar", "min": 15.00, "max": 20.00},
            {"nome": "Buquê de Rosas Vermelhas", "min": 15.00, "max": 30.00},
            {"nome": "Buquê de Tulipas", "min": 15.00, "max": 30.00},
            {"nome": "Tampa de Garrafa", "min": 0.10, "max": 0.20},
            {"nome": "Isca de Pesca", "min": 0.50, "max": 0.80},
            {"nome": "Orelhas", "min": 18.00, "max": 26.00},
            {"nome": "Caixote de Madeira", "min": 0.26, "max": 0.40},
        ]
    },
    "Jornal": {
        "icone": "📰", "cor": "#64748b",
        "produtos": [
            {"nome": "Cartaz para Poste", "min": 10.00, "max": 15.00},
            {"nome": "Seda", "min": 0.50, "max": 0.70},
            {"nome": "Impressão-Matérias", "min": 1.00, "max": 1.20},
            {"nome": "Rótulo", "min": 0.55, "max": 0.73},
            {"nome": "Carta de Coleção", "min": 1.00, "max": 1.30},
            {"nome": "Pacote de Cartas (5x cartas sortidas)", "min": 5.80, "max": 6.30},
            {"nome": "Tinta", "min": 1.00, "max": 1.50},
            {"nome": "Câmera Fotográfica", "min": 25.00, "max": 50.00},
        ]
    },
    "Ateliê": {
        "icone": "👔", "cor": "#14b8a6",
        "produtos": [
            {"nome": "Roupa Simples", "min": 50.00, "max": 80.00},
            {"nome": "Acessórios", "min": 30.00, "max": 50.00},
            {"nome": "Roupa Personalizada", "min": 100.00, "max": 150.00},
            {"nome": "Pomada de Cabelo", "min": 13.00, "max": 18.00},
            {"nome": "Toalha", "min": 1.00, "max": 2.00},
            {"nome": "Anel de Casamento", "min": 500.00, "max": 600.00},
        ]
    },
    "Cavalaria": {
        "icone": "🛡️", "cor": "#78716c",
        "produtos": [
            {"nome": "Placa de Arma", "min": 100.00, "max": 150.00},
            {"nome": "Escolta Particular", "min": 200.00, "max": 200.00},
        ]
    },
    "Tabacaria": {
        "icone": "🚬", "cor": "#854d0e",
        "produtos": [
            {"nome": "Charuto", "min": 4.00, "max": 5.00},
            {"nome": "Charuto de Chocolate", "min": 4.00, "max": 5.00},
            {"nome": "Cigarro", "min": 3.00, "max": 4.00},
            {"nome": "Goma de Tabaco", "min": 9.00, "max": 11.00},
            {"nome": "Pipe", "min": 8.00, "max": 10.00},
            {"nome": "Cigarro de Maconha", "min": 5.00, "max": 6.00},
            {"nome": "Óleo de Maconha", "min": 0.24, "max": 0.32},
        ]
    },
    "Tatuagem": {
        "icone": "💉", "cor": "#7c3aed",
        "produtos": [
            {"nome": "Tatuagens na Cabeça", "min": 1500.00, "max": 2000.00},
            {"nome": "Tatuagens no Peito/Costas", "min": 1500.00, "max": 2000.00},
            {"nome": "Ticket Tatuagem", "min": 2000.00, "max": 2500.00},
            {"nome": "Removedor de Tatuagem", "min": 1000.00, "max": 1200.00},
        ]
    },
    "Médico": {
        "icone": "🏥", "cor": "#059669",
        "produtos": [
            {"nome": "Seringa Médica", "min": 15.00, "max": 20.00},
            {"nome": "Antibiótico", "min": 7.00, "max": 11.00},
            {"nome": "Bandagem", "min": 5.00, "max": 10.00},
            {"nome": "Antídoto Hemotóxico", "min": 6.00, "max": 8.00},
            {"nome": "Antídoto Proteolítico", "min": 6.00, "max": 8.00},
            {"nome": "Tala", "min": 7.00, "max": 10.00},
            {"nome": "Energético", "min": 10.00, "max": 15.00},
            {"nome": "Vacina", "min": 25.00, "max": 30.00},
            {"nome": "Tratamento", "min": 70.00, "max": 75.00},
            {"nome": "Atendimento em Geral", "min": 15.00, "max": 15.00},
            {"nome": "Atendimento em Ambarino", "min": 20.00, "max": 20.00},
            {"nome": "Atendimento em New Austin", "min": 25.00, "max": 25.00},
            {"nome": "Atendimento em Guarma", "min": 20.00, "max": 20.00},
            {"nome": "Atendimento em Annesburg", "min": 20.00, "max": 20.00},
            {"nome": "Atendimento na Ilha Pirata", "min": 20.00, "max": 20.00},
        ]
    },
    "Mineradora": {
        "icone": "⛏️", "cor": "#1e40af",
        "produtos": [
            {"nome": "Minério de Ferro", "min": 0.18, "max": 0.26},
            {"nome": "Minério de Salitre", "min": 0.22, "max": 0.28},
            {"nome": "Minério de Cobre", "min": 0.22, "max": 0.28},
            {"nome": "Minério de Manganês", "min": 0.26, "max": 0.38},
            {"nome": "Minério de Enxofre", "min": 0.28, "max": 0.40},
            {"nome": "Minério de Prata", "min": 0.32, "max": 0.46},
            {"nome": "Minério de Platina", "min": 0.52, "max": 0.78},
            {"nome": "Minério de Ouro", "min": 0.68, "max": 0.95},
            {"nome": "Areia", "min": 0.11, "max": 0.16},
            {"nome": "Sal", "min": 0.11, "max": 0.18},
            {"nome": "Turfa", "min": 0.12, "max": 0.20},
        ]
    },
    "Madeireira": {
        "icone": "🪵", "cor": "#92400e",
        "produtos": [
            {"nome": "Madeira de Pinheiro", "min": 0.12, "max": 0.16},
            {"nome": "Madeira de Cedro", "min": 0.12, "max": 0.16},
            {"nome": "Madeira de Carvalho", "min": 0.12, "max": 0.16},
            {"nome": "Tora de Pinheiro", "min": 0.22, "max": 0.28},
            {"nome": "Tora de Cedro", "min": 0.22, "max": 0.28},
            {"nome": "Tora de Carvalho", "min": 0.22, "max": 0.28},
            {"nome": "Serragem", "min": 0.12, "max": 0.14},
            {"nome": "Carvão Vegetal", "min": 0.24, "max": 0.28},
            {"nome": "Tábua Leve", "min": 0.18, "max": 0.27},
            {"nome": "Tábua Bruta", "min": 0.22, "max": 0.33},
            {"nome": "Viga de Madeira", "min": 0.26, "max": 0.39},
            {"nome": "Lenha Rachada", "min": 0.28, "max": 0.34},
            {"nome": "Tábua de Carne", "min": 1.00, "max": 2.00},
            {"nome": "Essência de Madeira", "min": 0.28, "max": 0.42},
        ]
    },
    "Ferraria": {
        "icone": "⚒️", "cor": "#71717a",
        "produtos": [
            {"nome": "Lingote de Ferro", "min": 2.52, "max": 3.64},
            {"nome": "Lingote de Platina", "min": 7.28, "max": 10.92},
            {"nome": "Lingote de Ouro", "min": 9.52, "max": 13.30},
            {"nome": "Lingote de Cobre", "min": 5.60, "max": 11.20},
            {"nome": "Lingote de Aço", "min": 8.12, "max": 14.84},
            {"nome": "Faca de Esfolar", "min": 1.50, "max": 2.50},
            {"nome": "Cutelo de Açougueiro", "min": 1.00, "max": 1.50},
            {"nome": "Picareta", "min": 2.00, "max": 3.00},
            {"nome": "Pregos", "min": 0.10, "max": 0.20},
            {"nome": "Lança", "min": 50.00, "max": 70.00},
            {"nome": "Machado", "min": 3.00, "max": 4.50},
            {"nome": "Pá de Escavação", "min": 1.50, "max": 2.50},
            {"nome": "Pá de Escavação Profissional", "min": 15.00, "max": 17.00},
            {"nome": "Moedor", "min": 6.00, "max": 8.00},
            {"nome": "Seringa de Vidro", "min": 1.00, "max": 1.50},
            {"nome": "Cápsula de Metal", "min": 1.20, "max": 1.33},
        ]
    },
    "Nativos": {
        "icone": "🏹", "cor": "#d97706",
        "produtos": [
            {"nome": "Fogueira", "min": 5.00, "max": 10.00},
            {"nome": "Tomahawk", "min": 10.00, "max": 18.00},
            {"nome": "Tomahawk Pct (3x)", "min": 15.00, "max": 20.00},
            {"nome": "Tocha", "min": 10.00, "max": 15.00},
            {"nome": "Flecha Normal", "min": 5.00, "max": 7.00},
            {"nome": "Arco Simples", "min": 10.00, "max": 15.00},
            {"nome": "Laço Reforçado", "min": 10.00, "max": 12.00},
            {"nome": "Libid Gel Equino", "min": 100.00, "max": 200.00},
            {"nome": "Libid Gel Equino para Estábulo", "min": 50.00, "max": 100.00},
        ]
    },
    "Mercearia": {
        "icone": "🛒", "cor": "#0891b2",
        "produtos": [
            {"nome": "Livro de Sobrevivência", "min": 8.00, "max": 10.00},
            {"nome": "Sabonete", "min": 1.00, "max": 2.00},
            {"nome": "Areia Refinada", "min": 0.19, "max": 0.22},
            {"nome": "Calculadora", "min": 10.00, "max": 12.00},
            {"nome": "Bateria", "min": 1.00, "max": 1.30},
            {"nome": "Garrafa de Água", "min": 0.10, "max": 0.15},
        ]
    },
    "Bercario": {
        "icone": "🐄", "cor": "#16a34a",
        "produtos": [
            {"nome": "Gados", "min": 7.50, "max": 12.00},
            {"nome": "Porcos", "min": 7.50, "max": 12.00},
            {"nome": "Ovelhas", "min": 7.50, "max": 12.00},
            {"nome": "Galinhas", "min": 7.50, "max": 12.00},
            {"nome": "Mulas", "min": 7.50, "max": 12.00},
            {"nome": "Cabras", "min": 7.50, "max": 12.00},
            {"nome": "Búfalos", "min": 7.50, "max": 12.00},
        ]
    },
    "Agroindustria": {
        "icone": "🌱", "cor": "#65a30d",
        "produtos": [
            {"nome": "Ração para Gado", "min": 3.00, "max": 4.00},
            {"nome": "Ração para Porco", "min": 3.00, "max": 4.00},
            {"nome": "Ração para Ovelhas", "min": 3.00, "max": 4.00},
            {"nome": "Ração para Galinhas", "min": 3.00, "max": 4.00},
            {"nome": "Ração para Mulas", "min": 3.00, "max": 4.00},
            {"nome": "Ração para Cabras", "min": 3.00, "max": 4.00},
            {"nome": "Ração para Búfalos", "min": 3.00, "max": 4.00},
            {"nome": "Ração Premium para PET", "min": 2.00, "max": 3.00},
            {"nome": "KIT Médico para PET", "min": 25.00, "max": 30.00},
            {"nome": "Balde de Água", "min": 0.80, "max": 0.85},
            {"nome": "Fertilizante", "min": 0.50, "max": 0.60},
            {"nome": "Sementes", "min": 0.18, "max": 0.23},
            {"nome": "Rastelo", "min": 1.00, "max": 1.20},
            {"nome": "Água para PET", "min": 1.00, "max": 2.00},
            {"nome": "Adubo", "min": 0.15, "max": 0.20},
            {"nome": "Petbox", "min": 60.00, "max": 65.00},
            {"nome": "Gordura Animal Curada", "min": 0.16, "max": 0.24},
            {"nome": "Pano Grosso", "min": 0.20, "max": 0.36},
            {"nome": "Sal Refinado", "min": 0.21, "max": 0.22},
            {"nome": "Papelão Rústico", "min": 0.09, "max": 0.15},
            {"nome": "Fita Decorativa", "min": 0.16, "max": 0.26},
            {"nome": "Cola", "min": 0.20, "max": 0.50},
            {"nome": "Verniz", "min": 0.22, "max": 0.34},
            {"nome": "Garrafa de Água Vazia", "min": 0.08, "max": 0.12},
            {"nome": "Farinha", "min": 0.25, "max": 0.30},
            {"nome": "Libidgel Asneira", "min": 1.50, "max": 2.00},
            {"nome": "Libidgel Aviário", "min": 1.50, "max": 2.00},
            {"nome": "Libidgel Bovino", "min": 1.50, "max": 2.00},
            {"nome": "Libidgel Bufalino", "min": 1.50, "max": 2.00},
            {"nome": "Libidgel Caprino", "min": 1.50, "max": 2.00},
            {"nome": "Libidgel Ovino", "min": 1.50, "max": 2.00},
            {"nome": "Libidgel Suíno", "min": 1.50, "max": 2.00},
        ]
    },
    "Cartorio": {
        "icone": "📋", "cor": "#475569",
        "produtos": [
            {"nome": "Porte de Revólver", "min": 150.00, "max": 150.00},
            {"nome": "Porte de Pistola", "min": 175.00, "max": 175.00},
            {"nome": "Porte de Repetidora", "min": 225.00, "max": 225.00},
            {"nome": "Porte de Rifle", "min": 250.00, "max": 250.00},
            {"nome": "Porte de Shotgun", "min": 275.00, "max": 275.00},
            {"nome": "Porte para Armas de Herança", "min": 500.00, "max": 500.00},
            {"nome": "Porte Completo (Todos os tipos)", "min": 1400.00, "max": 1400.00},
            {"nome": "Alteração de Porte", "min": 150.00, "max": 150.00},
            {"nome": "Registro de Armamento", "min": 225.00, "max": 225.00},
            {"nome": "Casamento Simples", "min": 1250.00, "max": 1250.00},
            {"nome": "Casamento C/ Troca de Nome", "min": 1750.00, "max": 1750.00},
            {"nome": "Divórcio", "min": 2000.00, "max": 2000.00},
            {"nome": "Limpeza de Ficha (Unidade)", "min": 325.00, "max": 325.00},
            {"nome": "Mudança de Nome", "min": 2250.00, "max": 2250.00},
            {"nome": "Mudança de Sobrenome", "min": 1125.00, "max": 1125.00},
            {"nome": "Proteção de Ação de Rua", "min": 80.00, "max": 120.00},
            {"nome": "Proteção de Ação Fechada", "min": 150.00, "max": 200.00},
        ]
    },
    "Armaria": {
        "icone": "🔫", "cor": "#1f2937",
        "produtos": [
            {"nome": "Repetidora Winchester (Placa)", "min": 250.00, "max": 300.00},
            {"nome": "Repetidora Evans (Placa)", "min": 250.00, "max": 300.00},
            {"nome": "Repetidora Carabina", "min": 200.00, "max": 240.00},
            {"nome": "Repetidora Henry", "min": 180.00, "max": 220.00},
            {"nome": "Rifle de Ferrolho (Placa)", "min": 350.00, "max": 400.00},
            {"nome": "Rifle Springfield", "min": 300.00, "max": 350.00},
            {"nome": "Revólver Lemat (Placa)", "min": 210.00, "max": 230.00},
            {"nome": "Revólver Schofield", "min": 100.00, "max": 150.00},
            {"nome": "Revólver Double Action", "min": 120.00, "max": 160.00},
            {"nome": "Revólver Vaqueiro Mexicano", "min": 60.00, "max": 100.00},
            {"nome": "Pistola M1899 (Placa)", "min": 300.00, "max": 325.00},
            {"nome": "Pistola Mauser (Placa)", "min": 237.00, "max": 260.00},
            {"nome": "Pistola Semi-Auto", "min": 120.00, "max": 180.00},
            {"nome": "Pistola Volcanic", "min": 180.00, "max": 200.00},
            {"nome": "Shotgun Double Barrel (Placa)", "min": 280.00, "max": 350.00},
            {"nome": "Pano para Armas", "min": 8.00, "max": 12.00},
            {"nome": "Personalizações de Armas (por item)", "min": 60.00, "max": 100.00},
        ]
    },
    "Municao": {
        "icone": "💥", "cor": "#b91c1c",
        "produtos": [
            {"nome": "Munição de Pistola", "min": 5.50, "max": 7.50},
            {"nome": "Munição de Repetidora", "min": 6.50, "max": 9.00},
            {"nome": "Munição de Revólver", "min": 2.50, "max": 3.00},
            {"nome": "Munição de Rifle", "min": 8.00, "max": 10.50},
            {"nome": "Munição de Shotgun", "min": 9.00, "max": 11.00},
            {"nome": "Repetição Expressa", "min": 25.00, "max": 38.00},
            {"nome": "Revólver Expressa", "min": 18.00, "max": 26.00},
            {"nome": "Pistola Expressa", "min": 18.00, "max": 26.00},
            {"nome": "Rifle Expressa", "min": 45.00, "max": 62.00},
            {"nome": "Repetição de Velocidade", "min": 25.00, "max": 38.00},
            {"nome": "Revólver de Velocidade", "min": 18.00, "max": 26.00},
            {"nome": "Pistola de Velocidade", "min": 18.00, "max": 26.00},
            {"nome": "Rifle de Velocidade", "min": 45.00, "max": 62.00},
            {"nome": "Repetição de Ponto Dividido", "min": 25.00, "max": 38.00},
            {"nome": "Revólver de Ponto Dividido", "min": 18.00, "max": 26.00},
            {"nome": "Pistola de Ponto Dividido", "min": 18.00, "max": 26.00},
            {"nome": "Rifle de Ponto Dividido", "min": 45.00, "max": 62.00},
        ]
    },
    "Passaros": {
        "icone": "🦅", "cor": "#0ea5e9",
        "produtos": [
            {"nome": "Falcão Ferruginoso", "min": 100.00, "max": 120.00},
            {"nome": "Coruja Grande", "min": 300.00, "max": 320.00},
            {"nome": "Coruja Lendária", "min": 3000.00, "max": 3200.00},
            {"nome": "Águia Careca", "min": 400.00, "max": 420.00},
            {"nome": "Arara Azul/Amarela", "min": 300.00, "max": 320.00},
            {"nome": "Flamingo Rosado", "min": 400.00, "max": 420.00},
        ]
    }
}

def generate_code(name, suffix="_dt"):
    clean = re.sub(r'[^a-zA-Z0-9]', '_', name.lower())
    clean = re.sub(r'_+', '_', clean).strip('_')
    return f"{clean[:40]}{suffix}"

def seed_downtown():
    print("Seeding Downtown Base (ID: 1)...")
    
    # Ensure Base 1 exists
    res_base = supabase.table('bases_redm').select('*').eq('id', BASE_DOWNTOWN_ID).execute()
    if not res_base.data:
        print("Criando Base Downtown...")
        supabase.table('bases_redm').insert({'id': BASE_DOWNTOWN_ID, 'nome': 'Downtown', 'ativo': True}).execute()
    
    for cat_name, data in DOWNTOWN_DATA.items():
        print(f"Processing Category: {cat_name}...")
        
        # 1. Create or Get Type
        tipo_code = generate_code(cat_name)
        
        # Check if type exists
        res_type = supabase.table('tipos_empresa').select('id').eq('nome', cat_name).eq('base_redm_id', BASE_DOWNTOWN_ID).execute()
        
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
        for prod in data['produtos']:
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
                    'categoria': cat_name,
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
            else:
                # Optional: Update prices if needed
                pass

if __name__ == "__main__":
    seed_downtown()
