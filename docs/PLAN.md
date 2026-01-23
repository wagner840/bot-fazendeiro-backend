# Plan: Enable Real QR Code Generation (Asaas Production)

## Diagnosis
The system is currently generating "Sandbox" (test) QR codes because:
1. The `.env` file only contains `ASAAS_SANDBOX_API_KEY`.
2. The `api.py` script defaults to the Sandbox URL (`https://sandbox.asaas.com/api/v3`) when `ASAAS_API_URL` is not set.

## Goal
Switch the payment system to Production mode to generate real ("real") QR codes.

## User Actions Required
> [!IMPORTANT]
> **Production API Key Required**
> You must provide the **Production** API Key from your Asaas account. The current key in `.env` is a Sandbox key (`$aact_hmlg...`).

## Planned Changes

### 1. Environment Configuration (`.env`)
- **Action**: Add `ASAAS_API_KEY` (Production) and `ASAAS_API_URL`.
- **Change**:
```env
# Add these lines
ASAAS_API_KEY=your_production_key_here
ASAAS_API_URL=https://api.asaas.com/api/v3
```

### 2. Verification
- Restart the Backend API.
- Generate a new PIX charge via the Bot or Dashboard.
- Verify the QR Code is valid for payment in a real banking app.

## Execution Steps
1. **User**: Provide the Asaas Production API Key.
2. **Agent**: Update `.env` file.
3. **Agent**: Restart the backend service.
4. **Agent**: Test the connection (if possible/authorized).
