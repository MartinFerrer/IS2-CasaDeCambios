# Fix: Stripe Payment with Tauser Selection and Stock Verification

## Problem Description
When making a purchase operation with Stripe payment method, the error "No hay Tauser asociado" occurred because:
1. The Tauser ID was not being passed to the transaction creation endpoint
2. Stock verification was not happening before initiating the Stripe payment
3. Stock extraction (reservation) was not happening after successful Stripe payment

## Changes Made

### 1. New API Endpoint for Pre-Transaction Stock Verification
**File:** `app/apps/transacciones/views.py`

Added new endpoint `api_verificar_disponibilidad_tauser_previo()` that:
- Takes `tauser_id`, `divisa`, and `monto` as parameters
- Verifies stock availability BEFORE creating a transaction
- Uses `StockDivisaTauser.seleccionar_denominaciones_optimas()` to check if the Tauser has sufficient stock
- Returns JSON with `disponible` boolean and `mensaje` for user feedback

**Key features:**
- No transaction is created
- No stock is reserved
- Quick validation before payment flow begins

### 2. Updated URL Configuration
**File:** `app/apps/transacciones/urls.py`

Added new URL pattern:
```python
path("api/verificar-disponibilidad-tauser-previo/<int:tauser_id>/",
    views.api_verificar_disponibilidad_tauser_previo,
    name="api_verificar_disponibilidad_tauser_previo"
),
```

### 3. Frontend: Stock Verification Before Stripe Payment
**File:** `app/apps/transacciones/templates/realizar_transaccion.html`

Modified `showStripePaymentModal()` function to:
1. Validate that a Tauser is selected
2. For purchase operations (`compra`), call the new stock verification endpoint
3. Only proceed to create transaction and show Stripe modal if stock is available
4. Pass `tauser` parameter to the transaction creation endpoint

**Flow:**
```
User clicks "Realizar Transacción" with Stripe
  ↓
Validate Tauser is selected
  ↓
[FOR COMPRA] Call /api/verificar-disponibilidad-tauser-previo/{tauser_id}/?divisa=USD&monto=100
  ↓
If stock available:
  → Create transaction (with tauser parameter)
  → Show Stripe payment modal
  → Process payment
If stock insufficient:
  → Show error message
  → Don't proceed with payment
```

### 4. Backend: Stock Extraction After Successful Stripe Payment
**File:** `app/apps/transacciones/views.py`

Modified `confirm_stripe_payment()` function to:
1. Check if transaction is a purchase with Tauser collection (`compra` + `efectivo`)
2. When Stripe payment succeeds (`intent.status == "succeeded"`):
   - Verify Tauser is associated with transaction
   - Call `StockDivisaTauser.seleccionar_denominaciones_optimas()` to get optimal denominations
   - Call `extraer_divisas()` to reserve/extract stock from the Tauser
   - Set transaction state to "pendiente" (awaiting pickup at Tauser)
   - Set `fecha_pago` timestamp
3. Handle errors gracefully:
   - If no Tauser: Cancel transaction with appropriate reason
   - If insufficient stock: Cancel transaction and inform user
   - If extraction fails: Cancel transaction with error details

**Key logic:**
```python
if intent.status == "succeeded" and es_compra_con_tauser:
    # Get optimal denominations
    stock_info = StockDivisaTauser.seleccionar_denominaciones_optimas(...)

    if not stock_info:
        # Cancel transaction - insufficient stock
        transaccion.estado = "cancelada"
        transaccion.motivo_cancelacion = "Stock insuficiente..."
        return error response

    # Reserve stock
    extraer_divisas(
        tauser_id=transaccion.tauser.id,
        divisa_id=divisa_codigo,
        transaccion=transaccion,
        denominaciones_cantidades=stock_info,
        panel_admin=False  # Creates "pendiente" movement
    )

    transaccion.estado = "pendiente"  # Awaiting pickup
    transaccion.fecha_pago = timezone.now()
```

## Testing Checklist

### Pre-Transaction Stock Verification
- [ ] Purchase with Stripe when Tauser has sufficient stock → Success
- [ ] Purchase with Stripe when Tauser has insufficient stock → Error message, no transaction created
- [ ] Purchase with Stripe without selecting Tauser → Error message
- [ ] Verify stock check doesn't create transaction or reserve stock

### Transaction Creation
- [ ] Transaction is created with correct Tauser ID
- [ ] Transaction includes all required fields (divisas, montos, medios, tauser)
- [ ] Error "No hay Tauser asociado" no longer occurs

### Stripe Payment Processing
- [ ] Successful Stripe payment → Stock is extracted/reserved from Tauser
- [ ] Successful payment → Transaction state is "pendiente"
- [ ] Successful payment → `fecha_pago` is set
- [ ] Successful payment → MovimientoStock is created with type "salida" and state "pendiente"
- [ ] Payment with insufficient stock after payment → Transaction cancelled with appropriate message
- [ ] Payment fails → Transaction remains in previous state, no stock affected

### Edge Cases
- [ ] Race condition: Stock becomes unavailable between verification and payment
- [ ] Network error during stock extraction
- [ ] Multiple concurrent transactions for same Tauser
- [ ] Invalid denomination combinations

## Key Functions Used

### Stock Verification
- `StockDivisaTauser.seleccionar_denominaciones_optimas(tauser_id, divisa_codigo, monto)`
  - Returns list of `{'denominacion': int, 'cantidad': int}` or `None`
  - Uses dynamic programming to find optimal denomination combination
  - Respects available stock (`stock_libre`)

### Stock Extraction/Reservation
- `extraer_divisas(tauser_id, divisa_id, denominaciones_cantidades, transaccion, panel_admin=False)`
  - Creates `MovimientoStock` with type "salida"
  - When `panel_admin=False`: state is "pendiente" (reserves stock)
  - When `panel_admin=True`: state is "confirmado" (immediately removes stock)
  - Validates sufficient stock before extraction
  - Creates `MovimientoStockDetalle` for each denomination

## Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│ User initiates purchase transaction with Stripe payment          │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
            ┌────────────────────────┐
            │  Tauser selected?      │
            └────────┬───────────────┘
                     │ No
                     ├────────────────► Show error: "Select Tauser"
                     │ Yes
                     ▼
            ┌────────────────────────────────────────────┐
            │ Call api_verificar_disponibilidad_tauser   │
            │ - GET /api/.../previo/{tauser_id}/         │
            │ - Params: divisa, monto                    │
            └────────┬───────────────────────────────────┘
                     │
         ┌───────────┴──────────┐
         │                      │
    Insufficient            Sufficient
      Stock                   Stock
         │                      │
         ▼                      ▼
   Show error          ┌────────────────────┐
   message             │ Create Transaction │
   Don't proceed       │ - Include tauser   │
                       └────────┬───────────┘
                                │
                                ▼
                       ┌─────────────────────┐
                       │ Show Stripe Modal   │
                       │ - Enter card info   │
                       └────────┬────────────┘
                                │
                                ▼
                       ┌─────────────────────────┐
                       │ Create Payment Intent   │
                       └────────┬────────────────┘
                                │
                                ▼
                       ┌─────────────────────────┐
                       │ Confirm Card Payment    │
                       │ (Stripe.js)             │
                       └────────┬────────────────┘
                                │
                    ┌───────────┴──────────┐
                    │                      │
               Payment                Payment
               Failed               Succeeded
                    │                      │
                    ▼                      ▼
              Keep pending      ┌──────────────────────────┐
              state             │ confirm_stripe_payment() │
                                └──────────┬───────────────┘
                                           │
                                           ▼
                          ┌─────────────────────────────────┐
                          │ seleccionar_denominaciones...() │
                          │ - Check stock again             │
                          └──────────┬──────────────────────┘
                                     │
                         ┌───────────┴──────────┐
                         │                      │
                    Still have            No stock
                    sufficient            available
                       stock                   │
                         │                     ▼
                         ▼              Cancel transaction
                ┌─────────────────┐    Set motivo_cancelacion
                │ extraer_divisas │
                │ - Reserve stock │
                │ - panel_admin=F │
                └─────────┬───────┘
                          │
                          ▼
                ┌──────────────────────┐
                │ Transaction state:   │
                │ - estado: pendiente  │
                │ - fecha_pago: now    │
                │ Stock reserved!      │
                └──────────────────────┘
```

## Notes

- The `extraer_divisas()` function with `panel_admin=False` creates a "pendiente" movement which reserves stock but doesn't immediately remove it from the Tauser
- This allows the transaction to be completed later when the customer picks up at the Tauser
- If payment fails or is cancelled, the reservation can be rolled back using `cancelar_movimiento()`
- The double-check of stock (before payment and after payment) prevents race conditions where stock becomes unavailable during payment processing
