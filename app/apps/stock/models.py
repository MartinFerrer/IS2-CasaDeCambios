"""Modelos para la aplicación de stock.

Este módulo define los modelos para gestionar el stock de divisas por tauser
y rastrear los movimientos del stock.
"""


from django.core.exceptions import ValidationError
from django.db import models


class StockDivisaTauser(models.Model):
    """Modelo que representa el stock de una divisa para un tauser específico.

    Attributes:
        tauser (ForeignKey): Referencia al tauser propietario del stock.
        divisa (ForeignKey): Referencia a la divisa del stock.
        denominacion (IntegerField): Denominación del billete/moneda.
        stock (IntegerField): Cantidad disponible en stock.
        stock_reservado (IntegerField): Cantidad reservada para transacciones pendientes.
        fecha_creacion (DateTimeField): Fecha de creación del registro.
        fecha_modificacion (DateTimeField): Fecha de última modificación.

    """

    tauser = models.ForeignKey(
        'tauser.Tauser',
        on_delete=models.PROTECT,
        verbose_name='Tauser'
    )
    divisa = models.ForeignKey(
        'operaciones.Divisa',
        on_delete=models.PROTECT,
        verbose_name='Divisa'
    )
    denominacion = models.IntegerField(
        default=0,
        verbose_name='Denominación',
        help_text='Denominación del billete/moneda'
    )
    stock = models.IntegerField(
        default=0,
        verbose_name='Stock Disponible',
        help_text='Cantidad disponible en stock'
    )
    stock_reservado = models.IntegerField(
        default=0,
        verbose_name='Stock Reservado',
        help_text='Cantidad reservada para transacciones pendientes'
    )
    fecha_creacion = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Fecha de Creación'
    )
    fecha_modificacion = models.DateTimeField(
        auto_now=True,
        verbose_name='Fecha de Modificación'
    )

    class Meta:
        """Configuración para el modelo StockDivisaTauser."""

        verbose_name = 'Stock de Divisa por Tauser'
        verbose_name_plural = 'Stocks de Divisas por Tauser'
        ordering = ['tauser__nombre', 'divisa__codigo', 'denominacion']
        unique_together = ['tauser', 'divisa', 'denominacion']

    def __str__(self):
        """Representación en string del objeto."""
        return f"{self.tauser.nombre} - {self.divisa.codigo} {self.denominacion}"

    def clean(self):
        """Validaciones del modelo antes de guardar."""
        if self.denominacion <= 0:
            raise ValidationError('La denominación debe ser mayor a cero.')

        if self.stock < 0:
            raise ValidationError('El stock no puede ser negativo.')

        if self.stock_reservado < 0:
            raise ValidationError('El stock reservado no puede ser negativo.')

        if self.stock_reservado > self.stock:
            raise ValidationError('El stock reservado no puede ser mayor al stock disponible.')

    @property
    def stock_libre(self):
        """Calcula el stock libre (disponible menos reservado)."""
        return self.stock - self.stock_reservado

    def reservar_stock(self, cantidad):
        """Reserva una cantidad del stock para una transacción pendiente.
        
        Args:
            cantidad (Decimal): Cantidad a reservar.
            
        Returns:
            bool: True si se pudo reservar, False si no hay suficiente stock.

        """
        if self.stock_libre >= cantidad:
            self.stock_reservado += cantidad
            return True
        return False

    def liberar_stock_reservado(self, cantidad):
        """Libera una cantidad del stock reservado.
        
        Args:
            cantidad (Decimal): Cantidad a liberar.

        """
        if cantidad <= self.stock_reservado:
            self.stock_reservado -= cantidad

    def confirmar_movimiento(self, cantidad):
        """Confirma un movimiento del stock reservado (lo descuenta del stock total).
        
        Args:
            cantidad (int): Cantidad a confirmar.

        """
        if cantidad <= self.stock_reservado:
            self.stock -= cantidad
            self.stock_reservado -= cantidad

    @classmethod
    def obtener_stock_total_divisa(cls, tauser, divisa):
        """Obtiene el stock total de una divisa para un tauser (suma todas las denominaciones).
        
        Args:
            tauser: Instancia del tauser
            divisa: Instancia de la divisa
            
        Returns:
            dict: Diccionario con el valor total disponible y reservado

        """
        stocks = cls.objects.filter(tauser=tauser, divisa=divisa)
        total_disponible = sum(s.stock * s.denominacion for s in stocks)
        total_reservado = sum(s.stock_reservado * s.denominacion for s in stocks)

        return {
            'total_disponible': total_disponible,
            'total_reservado': total_reservado,
            'total_libre': total_disponible - total_reservado
        }

    @classmethod
    def seleccionar_denominaciones_optimas(cls, tauser, divisa, monto_objetivo):
        """Selecciona las denominaciones óptimas para cubrir un monto objetivo.
        
        Args:
            tauser: Instancia del tauser
            divisa: Instancia de la divisa
            monto_objetivo (int): Monto que se quiere cubrir
            
        Returns:
            list: Lista de diccionarios con denominación y cantidad necesaria

        """
        stocks = cls.objects.filter(
            tauser=tauser,
            divisa=divisa,
            stock__gt=0
        ).order_by('-denominacion')  # Empezar por denominaciones más grandes

        resultado = []
        monto_restante = monto_objetivo

        for stock in stocks:
            if monto_restante <= 0:
                break

            denominacion = stock.denominacion
            cantidad_necesaria = min(
                monto_restante // denominacion,  # Cuántos billetes de esta denominación necesito
                stock.stock_libre  # Cuántos tengo disponibles
            )

            if cantidad_necesaria > 0:
                resultado.append({
                    'stock_id': stock.pk,
                    'denominacion': denominacion,
                    'cantidad': cantidad_necesaria,
                    'valor_total': denominacion * cantidad_necesaria
                })
                monto_restante -= denominacion * cantidad_necesaria

        # Verificar si se pudo cubrir el monto completo
        if monto_restante > 0:
            return None  # No hay suficiente stock

        return resultado


class MovimientoStock(models.Model):
    """Modelo para rastrear los movimientos del stock de divisas.

    Attributes:
        tauser (ForeignKey): Referencia al tauser afectado por el movimiento.
        divisa (ForeignKey): Referencia a la divisa del movimiento.
        transaccion (ForeignKey): Referencia a la transacción asociada (opcional).
        tipo_movimiento (CharField): Tipo de movimiento (entrada, salida, reserva, liberacion).
        estado (CharField): Estado del movimiento (pendiente, confirmado, cancelado).
        motivo (TextField): Motivo o descripción del movimiento.
        fecha_creacion (DateTimeField): Fecha de creación del movimiento.
        fecha_procesamiento (DateTimeField): Fecha de procesamiento del movimiento.

    """

    TIPOS_MOVIMIENTO = [
        ('entrada', 'Entrada'),
        ('salida', 'Salida'),
        ('reserva', 'Reserva'),
        ('liberacion', 'Liberación'),
        ('ajuste', 'Ajuste'),
    ]

    ESTADOS_MOVIMIENTO = [
        ('pendiente', 'Pendiente'),
        ('confirmado', 'Confirmado'),
        ('cancelado', 'Cancelado'),
    ]

    tauser = models.ForeignKey(
        'tauser.Tauser',
        on_delete=models.PROTECT,
        verbose_name='Tauser'
    )

    divisa = models.ForeignKey(
        'operaciones.Divisa',
        on_delete=models.PROTECT,
        verbose_name='Divisa'
    )

    transaccion = models.ForeignKey(
        'transacciones.Transaccion',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Transacción',
        help_text='Transacción asociada'
    )

    tipo_movimiento = models.CharField(
        max_length=20,
        choices=TIPOS_MOVIMIENTO,
        verbose_name='Tipo de Movimiento'
    )

    estado = models.CharField(
        max_length=20,
        choices=ESTADOS_MOVIMIENTO,
        default='pendiente',
        verbose_name='Estado'
    )

    motivo = models.TextField(
        blank=True,
        default='',
        verbose_name='Motivo',
        help_text='Descripción del motivo del movimiento'
    )
    fecha_creacion = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Fecha de Creación'
    )
    fecha_procesamiento = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Fecha de Procesamiento'
    )

    class Meta:
        """Configuración para el modelo MovimientoStock."""

        verbose_name = 'Movimiento de Stock'
        verbose_name_plural = 'Movimientos de Stock'
        ordering = ['-fecha_creacion']

    def __str__(self):
        """Representación en string del objeto."""
        return f"{self.tipo_movimiento} - {self.tauser.nombre} - {self.divisa.codigo}"

    def clean(self):
        """Validaciones del modelo antes de guardar."""
        # Las validaciones específicas de cantidad y denominación
        # ahora se manejan en MovimientoStockDetalle
        pass

    def valor_total_movimiento(self):
        """Calcula el valor total del movimiento sumando todos los detalles."""
        return sum(detalle.valor_total for detalle in self.detalles.all())

    def resumen_denominaciones(self):
        """Retorna un resumen de las denominaciones involucradas en el movimiento."""
        return ", ".join([
            f"{detalle.cantidad}x{detalle.denominacion}"
            for detalle in self.detalles.all().order_by('-denominacion')
        ])

class MovimientoStockDetalle(models.Model):
    """Detalle de los movimientos de stock por denominación.

    Attributes:
        movimiento_stock (ForeignKey): Referencia al movimiento de stock.
        cantidad (IntegerField): Cantidad del movimiento.
        denominacion (IntegerField): Denominación del billete/moneda.

    """

    movimiento_stock = models.ForeignKey(
        MovimientoStock,
        on_delete=models.CASCADE,
        related_name='detalles',
        verbose_name='Movimiento de Stock'
    )
    cantidad = models.IntegerField(
        default=0,
        verbose_name='Cantidad',
        help_text='Cantidad de billetes/monedas de esta denominación'
    )
    denominacion = models.IntegerField(
        default=0,
        verbose_name='Denominación',
        help_text='Denominación del billete/moneda'
    )

    class Meta:
        """Configuración para el modelo MovimientoStockDetalle."""

        verbose_name = 'Detalle de Movimiento de Stock'
        verbose_name_plural = 'Detalles de Movimientos de Stock'
        ordering = ['-denominacion']
        unique_together = ['movimiento_stock', 'denominacion']

    def __str__(self):
        """Representación en string del objeto."""
        return f"{self.cantidad} x {self.denominacion} {self.movimiento_stock.divisa.codigo}"

    def clean(self):
        """Validaciones del modelo antes de guardar."""
        if self.cantidad <= 0:
            raise ValidationError('La cantidad debe ser mayor a cero.')

        if self.denominacion <= 0:
            raise ValidationError('La denominación debe ser mayor a cero.')

    @property
    def valor_total(self):
        """Calcula el valor total de este detalle (cantidad × denominación)."""
        return self.cantidad * self.denominacion
