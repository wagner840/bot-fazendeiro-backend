-- Optimizing indexes and hardening security
-- Created at 2026-01-26 19:56:16

-- Add missing foreign key indexes
CREATE INDEX IF NOT EXISTS idx_empresas_tipo_empresa ON empresas(tipo_empresa_id);
CREATE INDEX IF NOT EXISTS idx_estoque_produtos_empresa ON estoque_produtos(empresa_id);
CREATE INDEX IF NOT EXISTS idx_assinaturas_servidor ON assinaturas(servidor_id);
CREATE INDEX IF NOT EXISTS idx_assinaturas_plano ON assinaturas(plano_id);
CREATE INDEX IF NOT EXISTS idx_pagamentos_pix_assinatura ON pagamentos_pix(assinatura_id);
CREATE INDEX IF NOT EXISTS idx_pagamentos_pix_plano ON pagamentos_pix(plano_id);
CREATE INDEX IF NOT EXISTS idx_servidores_base_redm ON servidores(base_redm_id);
CREATE INDEX IF NOT EXISTS idx_tipos_empresa_base_redm ON tipos_empresa(base_redm_id);

-- Enable RLS on bases_redm
ALTER TABLE IF EXISTS bases_redm ENABLE ROW LEVEL SECURITY;
