import logging
from urllib.parse import urlparse
import xmlrpc.client

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class OdooRemoteConnection(models.Model):
    _name = "odoo.remote.connection"
    _description = "Odoo Remote Connection"

    name = fields.Char(string="Nombre", required=True)
    url = fields.Char(
        string="URL",
        required=True,
        help="https://dfestamcbo-p1-31394918.dev.odoo.com",
    )
    database_name = fields.Char(string="Base de Datos", required=True)
    username = fields.Char(string="Usuario", required=True)
    password = fields.Char(string="Contraseña", required=True, password=True)
    state = fields.Selection(
        selection=[("draft", "Sin Probar"), ("connected", "Conectado"), ("failed", "Fallido")],
        string="Estado",
        default="draft",
        readonly=True,
    )
    uid = fields.Integer(string="UID Remoto", readonly=True)
    server_version = fields.Char(string="Versión Servidor", readonly=True)
    last_tested_on = fields.Datetime(string="Última Prueba", readonly=True)
    active = fields.Boolean(default=True)

    def _prepare_remote_pos_session_vals(self, session):
        return {
            "name": session.name,
            "source_database": self.env.cr.dbname,
            "source_session_id": session.id,
            "state": session.state,
            "config_name": session.config_id.display_name if session.config_id else False,
            "user_name": session.user_id.display_name if session.user_id else False,
            "start_at": session.start_at or False,
            "stop_at": session.stop_at or False,
            "total_orders": len(session.order_ids),
            "total_amount": sum(session.order_ids.mapped("amount_total")),
        }

    def _prepare_remote_pos_order_vals(self, order, remote_session_id):
        return {
            "remote_session_id": remote_session_id,
            "source_database": self.env.cr.dbname,
            "source_order_id": order.id,
            "name": order.name,
            "pos_reference": order.pos_reference or False,
            "date_order": order.date_order or False,
            "state": order.state,
            "partner_name": order.partner_id.display_name if order.partner_id else False,
            "user_name": order.user_id.display_name if order.user_id else False,
            "lines_count": len(order.lines),
            "amount_total": order.amount_total,
        }

    def _prepare_remote_pos_order_line_vals(self, line, remote_order_id):
        product_default_code = False
        if line.product_id and line.product_id.product_tmpl_id:
            product_default_code = line.product_id.product_tmpl_id.default_code
        return {
            "remote_order_id": remote_order_id,
            "source_database": self.env.cr.dbname,
            "source_order_line_id": line.id,
            "order_name": line.order_id.name if line.order_id else False,
            "product_name": line.full_product_name or (line.product_id.display_name if line.product_id else False),
            "product_default_code": product_default_code,
            "qty": line.qty,
            "price_unit": line.price_unit,
            "discount": line.discount,
            "price_subtotal": line.price_subtotal,
            "price_subtotal_incl": line.price_subtotal_incl,
        }

    def _prepare_remote_pos_payment_vals(self, payment, remote_session_id, remote_order_id):
        return {
            "remote_session_id": remote_session_id,
            "remote_order_id": remote_order_id,
            "source_database": self.env.cr.dbname,
            "source_payment_id": payment.id,
            "session_name": payment.session_id.name if payment.session_id else False,
            "order_name": payment.pos_order_id.name if payment.pos_order_id else False,
            "payment_method_name": payment.payment_method_id.display_name if payment.payment_method_id else False,
            "amount": payment.amount,
            "payment_date": payment.payment_date or False,
        }

    def _prepare_remote_stock_move_vals(self, move, remote_session_id, remote_order_id):
        product_default_code = False
        if move.product_id and move.product_id.product_tmpl_id:
            product_default_code = move.product_id.product_tmpl_id.default_code
        return {
            "remote_session_id": remote_session_id,
            "remote_order_id": remote_order_id,
            "source_database": self.env.cr.dbname,
            "source_stock_move_id": move.id,
            "session_name": move.picking_id.pos_order_id.session_id.name if move.picking_id and move.picking_id.pos_order_id and move.picking_id.pos_order_id.session_id else False,
            "order_name": move.picking_id.pos_order_id.name if move.picking_id and move.picking_id.pos_order_id else False,
            "picking_name": move.picking_id.name if move.picking_id else False,
            "name": move.name,
            "reference": move.reference or False,
            "product_name": move.product_id.display_name if move.product_id else False,
            "product_default_code": product_default_code,
            "product_uom_qty": move.product_uom_qty,
            "quantity_done": move.quantity_done,
            "state": move.state,
            "date": move.date or False,
            "location_name": move.location_id.display_name if move.location_id else False,
            "location_dest_name": move.location_dest_id.display_name if move.location_dest_id else False,
        }

    def _prepare_receiver_session_vals(self, session, remote_connection_id):
        return {
            "connection_id": remote_connection_id,
            "remote_id": session.id,
            "name": session.name,
            "state": session.state,
            "start_at": session.start_at or False,
            "stop_at": session.stop_at or False,
            "config_name": session.config_id.display_name if session.config_id else False,
            "user_name": session.user_id.display_name if session.user_id else False,
            "cash_register_balance_start": session.cash_register_balance_start,
            "cash_register_balance_end_real": session.cash_register_balance_end_real,
            "remote_write_date": session.write_date or False,
            "payload": str(
                {
                    "source_database": self.env.cr.dbname,
                    "source_session_id": session.id,
                    "name": session.name,
                    "state": session.state,
                }
            ),
        }

    def _prepare_receiver_order_vals(self, order, remote_connection_id):
        return {
            "connection_id": remote_connection_id,
            "remote_id": order.id,
            "name": order.name,
            "pos_reference": order.pos_reference or False,
            "date_order": order.date_order or False,
            "state": order.state,
            "partner_name": order.partner_id.display_name if order.partner_id else False,
            "amount_tax": order.amount_tax,
            "amount_total": order.amount_total,
            "amount_paid": order.amount_paid,
            "session_remote_id": order.session_id.id if order.session_id else False,
            "session_name": order.session_id.name if order.session_id else False,
            "num_factura": getattr(order, 'num_factura', False),  # <-- AÑADIDO PARA ENVIAR
            "remote_write_date": order.write_date or False,
            "payload": str(
                {
                    "source_database": self.env.cr.dbname,
                    "source_order_id": order.id,
                    "name": order.name,
                    "state": order.state,
                }
            ),
        }
    def _prepare_receiver_order_line_vals(self, line, remote_connection_id):
        product_default_code = False
        if line.product_id and line.product_id.product_tmpl_id:
            product_default_code = line.product_id.product_tmpl_id.default_code
        return {
            "connection_id": remote_connection_id,
            "remote_id": line.id,
            "order_remote_id": line.order_id.id if line.order_id else False,
            "order_name": line.order_id.name if line.order_id else False,
            "product_name": line.full_product_name or (line.product_id.display_name if line.product_id else False),
            "product_default_code": product_default_code,
            "qty": line.qty,
            "price_unit": line.price_unit,
            "discount": line.discount,
            "price_subtotal": line.price_subtotal,
            "price_subtotal_incl": line.price_subtotal_incl,
            "remote_write_date": line.write_date or False,
            "payload": str(
                {
                    "source_database": self.env.cr.dbname,
                    "source_order_line_id": line.id,
                    "order_name": line.order_id.name if line.order_id else False,
                }
            ),
        }

    def _prepare_receiver_payment_vals(self, payment, remote_connection_id):
        return {
            "connection_id": remote_connection_id,
            "remote_id": payment.id,
            "session_remote_id": payment.session_id.id if payment.session_id else False,
            "session_name": payment.session_id.name if payment.session_id else False,
            "order_remote_id": payment.pos_order_id.id if payment.pos_order_id else False,
            "order_name": payment.pos_order_id.name if payment.pos_order_id else False,
            "payment_method_name": payment.payment_method_id.display_name if payment.payment_method_id else False,
            "amount": payment.amount,
            "payment_date": payment.payment_date or False,
            "remote_write_date": payment.write_date or False,
            "payload": str(
                {
                    "source_database": self.env.cr.dbname,
                    "source_payment_id": payment.id,
                    "order_name": payment.pos_order_id.name if payment.pos_order_id else False,
                }
            ),
        }

    def _prepare_receiver_stock_move_vals(self, move, remote_connection_id):
        pos_order = move.picking_id.pos_order_id if move.picking_id else False
        pos_session = pos_order.session_id if pos_order else False
        product_default_code = False
        if move.product_id and move.product_id.product_tmpl_id:
            product_default_code = move.product_id.product_tmpl_id.default_code
        return {
            "connection_id": remote_connection_id,
            "remote_id": move.id,
            "session_remote_id": pos_session.id if pos_session else False,
            "session_name": pos_session.name if pos_session else False,
            "order_remote_id": pos_order.id if pos_order else False,
            "order_name": pos_order.name if pos_order else False,
            "picking_name": move.picking_id.name if move.picking_id else False,
            "name": move.name,
            "reference": move.reference or False,
            "product_name": move.product_id.display_name if move.product_id else False,
            "product_default_code": product_default_code,
            "product_uom_qty": move.product_uom_qty,
            "quantity_done": move.quantity_done,
            "state": move.state,
            "date": move.date or False,
            "location_name": move.location_id.display_name if move.location_id else False,
            "location_dest_name": move.location_dest_id.display_name if move.location_dest_id else False,
            "remote_write_date": move.write_date or False,
            "payload": str(
                {
                    "source_database": self.env.cr.dbname,
                    "source_stock_move_id": move.id,
                    "order_name": pos_order.name if pos_order else False,
                }
            ),
        }

    def _iter_order_stock_moves(self, order):
        pickings = order.picking_ids
        moves = pickings.mapped("move_ids_without_package")
        if not moves and pickings and "move_lines" in pickings._fields:
            moves = pickings.mapped("move_lines")
        return moves

    def send_pos_sessions(self, sessions):
        self.ensure_one()
        uid, models_proxy, _common_proxy = self.get_remote_session()
        target_type = self._get_remote_target_type(models_proxy, uid)

        if target_type == "receiver":
            try:
                return self._send_pos_to_receiver(models_proxy, uid, sessions)
            except Exception as error:
                if self._is_remote_access_error(error):
                    if self._has_remote_mirror_models(models_proxy, uid):
                        return self._send_pos_to_mirror(models_proxy, uid, sessions)
                    raise UserError(
                        _(
                            "La base destino tiene instalado POS Remote Sync Receiver, pero el usuario remoto no tiene permisos suficientes. "
                            "Asigna el grupo POS Remote Sync Manager al usuario remoto o agrega ACL para base.group_system en esos modelos. "
                            "Detalle técnico: %(error)s",
                            error=str(error),
                        )
                    ) from error
                raise

        return self._send_pos_to_mirror(models_proxy, uid, sessions)

    def _send_pos_to_mirror(self, models_proxy, uid, sessions):
        self._ensure_remote_pos_models(models_proxy, uid)
        session_sent = 0
        order_sent = 0
        line_sent = 0
        payment_sent = 0
        stock_move_sent = 0

        for session in sessions:
            domain_session = [
                ["source_database", "=", self.env.cr.dbname],
                ["source_session_id", "=", session.id],
            ]
            remote_session_ids = models_proxy.execute_kw(
                self.database_name,
                uid,
                self.password,
                "odoo.remote.pos.session",
                "search",
                [domain_session],
                {"limit": 1},
            )
            session_vals = self._prepare_remote_pos_session_vals(session)
            if remote_session_ids:
                remote_session_id = remote_session_ids[0]
                models_proxy.execute_kw(
                    self.database_name,
                    uid,
                    self.password,
                    "odoo.remote.pos.session",
                    "write",
                    [[remote_session_id], session_vals],
                )
            else:
                remote_session_id = models_proxy.execute_kw(
                    self.database_name,
                    uid,
                    self.password,
                    "odoo.remote.pos.session",
                    "create",
                    [session_vals],
                )
            session_sent += 1

            for order in session.order_ids:
                domain_order = [
                    ["source_database", "=", self.env.cr.dbname],
                    ["source_order_id", "=", order.id],
                ]
                remote_order_ids = models_proxy.execute_kw(
                    self.database_name,
                    uid,
                    self.password,
                    "odoo.remote.pos.order",
                    "search",
                    [domain_order],
                    {"limit": 1},
                )
                order_vals = self._prepare_remote_pos_order_vals(order, remote_session_id)
                if remote_order_ids:
                    models_proxy.execute_kw(
                        self.database_name,
                        uid,
                        self.password,
                        "odoo.remote.pos.order",
                        "write",
                        [[remote_order_ids[0]], order_vals],
                    )
                else:
                    models_proxy.execute_kw(
                        self.database_name,
                        uid,
                        self.password,
                        "odoo.remote.pos.order",
                        "create",
                        [order_vals],
                    )
                order_sent += 1

                for line in order.lines:
                    domain_line = [
                        ["source_database", "=", self.env.cr.dbname],
                        ["source_order_line_id", "=", line.id],
                    ]
                    remote_line_ids = models_proxy.execute_kw(
                        self.database_name,
                        uid,
                        self.password,
                        "odoo.remote.pos.order.line",
                        "search",
                        [domain_line],
                        {"limit": 1},
                    )
                    line_vals = self._prepare_remote_pos_order_line_vals(line, remote_order_id)
                    if remote_line_ids:
                        models_proxy.execute_kw(
                            self.database_name,
                            uid,
                            self.password,
                            "odoo.remote.pos.order.line",
                            "write",
                            [[remote_line_ids[0]], line_vals],
                        )
                    else:
                        models_proxy.execute_kw(
                            self.database_name,
                            uid,
                            self.password,
                            "odoo.remote.pos.order.line",
                            "create",
                            [line_vals],
                        )
                    line_sent += 1

                for payment in order.payment_ids:
                    domain_payment = [
                        ["source_database", "=", self.env.cr.dbname],
                        ["source_payment_id", "=", payment.id],
                    ]
                    remote_payment_ids = models_proxy.execute_kw(
                        self.database_name,
                        uid,
                        self.password,
                        "odoo.remote.pos.payment",
                        "search",
                        [domain_payment],
                        {"limit": 1},
                    )
                    payment_vals = self._prepare_remote_pos_payment_vals(payment, remote_session_id, remote_order_id)
                    if remote_payment_ids:
                        models_proxy.execute_kw(
                            self.database_name,
                            uid,
                            self.password,
                            "odoo.remote.pos.payment",
                            "write",
                            [[remote_payment_ids[0]], payment_vals],
                        )
                    else:
                        models_proxy.execute_kw(
                            self.database_name,
                            uid,
                            self.password,
                            "odoo.remote.pos.payment",
                            "create",
                            [payment_vals],
                        )
                    payment_sent += 1

                for move in self._iter_order_stock_moves(order):
                    domain_move = [
                        ["source_database", "=", self.env.cr.dbname],
                        ["source_stock_move_id", "=", move.id],
                    ]
                    remote_move_ids = models_proxy.execute_kw(
                        self.database_name,
                        uid,
                        self.password,
                        "odoo.remote.stock.move",
                        "search",
                        [domain_move],
                        {"limit": 1},
                    )
                    move_vals = self._prepare_remote_stock_move_vals(move, remote_session_id, remote_order_id)
                    if remote_move_ids:
                        models_proxy.execute_kw(
                            self.database_name,
                            uid,
                            self.password,
                            "odoo.remote.stock.move",
                            "write",
                            [[remote_move_ids[0]], move_vals],
                        )
                    else:
                        models_proxy.execute_kw(
                            self.database_name,
                            uid,
                            self.password,
                            "odoo.remote.stock.move",
                            "create",
                            [move_vals],
                        )
                    stock_move_sent += 1

        return session_sent, order_sent, line_sent, payment_sent, stock_move_sent

    def _is_remote_access_error(self, error):
        message = str(error or "").lower()
        return (
            isinstance(error, xmlrpc.client.Fault)
            and (
                "accesserror" in message
                or "no puede ingresar" in message
                or "permission" in message
                or "acceso" in message
            )
        )

    def _has_remote_mirror_models(self, models_proxy, uid):
        return self._remote_model_exists(models_proxy, uid, "odoo.remote.pos.session") and self._remote_model_exists(
            models_proxy, uid, "odoo.remote.pos.order"
        ) and self._remote_model_exists(models_proxy, uid, "odoo.remote.pos.order.line") and self._remote_model_exists(
            models_proxy, uid, "odoo.remote.pos.payment"
        ) and self._remote_model_exists(models_proxy, uid, "odoo.remote.stock.move")

    def _send_pos_to_receiver(self, models_proxy, uid, sessions):
        remote_connection_id = self._find_remote_receiver_connection_id(models_proxy, uid)
        session_sent = 0
        order_sent = 0
        line_sent = 0
        payment_sent = 0
        stock_move_sent = 0

        for session in sessions:
            domain_session = [
                ["connection_id", "=", remote_connection_id],
                ["remote_id", "=", session.id],
            ]
            remote_session_ids = models_proxy.execute_kw(
                self.database_name,
                uid,
                self.password,
                "pos.remote.received.session",
                "search",
                [domain_session],
                {"limit": 1},
            )
            session_vals = self._prepare_receiver_session_vals(session, remote_connection_id)
            if remote_session_ids:
                models_proxy.execute_kw(
                    self.database_name,
                    uid,
                    self.password,
                    "pos.remote.received.session",
                    "write",
                    [[remote_session_ids[0]], session_vals],
                )
            else:
                models_proxy.execute_kw(
                    self.database_name,
                    uid,
                    self.password,
                    "pos.remote.received.session",
                    "create",
                    [session_vals],
                )
            session_sent += 1

            for order in session.order_ids:
                domain_order = [
                    ["connection_id", "=", remote_connection_id],
                    ["remote_id", "=", order.id],
                ]
                remote_order_ids = models_proxy.execute_kw(
                    self.database_name,
                    uid,
                    self.password,
                    "pos.remote.received.order",
                    "search",
                    [domain_order],
                    {"limit": 1},
                )
                order_vals = self._prepare_receiver_order_vals(order, remote_connection_id)
                if remote_order_ids:
                    models_proxy.execute_kw(
                        self.database_name,
                        uid,
                        self.password,
                        "pos.remote.received.order",
                        "write",
                        [[remote_order_ids[0]], order_vals],
                    )
                else:
                    models_proxy.execute_kw(
                        self.database_name,
                        uid,
                        self.password,
                        "pos.remote.received.order",
                        "create",
                        [order_vals],
                    )
                order_sent += 1

                for line in order.lines:
                    domain_line = [
                        ["connection_id", "=", remote_connection_id],
                        ["remote_id", "=", line.id],
                    ]
                    remote_line_ids = models_proxy.execute_kw(
                        self.database_name,
                        uid,
                        self.password,
                        "pos.remote.received.order.line",
                        "search",
                        [domain_line],
                        {"limit": 1},
                    )
                    line_vals = self._prepare_receiver_order_line_vals(line, remote_connection_id)
                    if remote_line_ids:
                        models_proxy.execute_kw(
                            self.database_name,
                            uid,
                            self.password,
                            "pos.remote.received.order.line",
                            "write",
                            [[remote_line_ids[0]], line_vals],
                        )
                    else:
                        models_proxy.execute_kw(
                            self.database_name,
                            uid,
                            self.password,
                            "pos.remote.received.order.line",
                            "create",
                            [line_vals],
                        )
                    line_sent += 1

                for payment in order.payment_ids:
                    domain_payment = [
                        ["connection_id", "=", remote_connection_id],
                        ["remote_id", "=", payment.id],
                    ]
                    remote_payment_ids = models_proxy.execute_kw(
                        self.database_name,
                        uid,
                        self.password,
                        "pos.remote.received.payment",
                        "search",
                        [domain_payment],
                        {"limit": 1},
                    )
                    payment_vals = self._prepare_receiver_payment_vals(payment, remote_connection_id)
                    if remote_payment_ids:
                        models_proxy.execute_kw(
                            self.database_name,
                            uid,
                            self.password,
                            "pos.remote.received.payment",
                            "write",
                            [[remote_payment_ids[0]], payment_vals],
                        )
                    else:
                        models_proxy.execute_kw(
                            self.database_name,
                            uid,
                            self.password,
                            "pos.remote.received.payment",
                            "create",
                            [payment_vals],
                        )
                    payment_sent += 1

                for move in self._iter_order_stock_moves(order):
                    domain_move = [
                        ["connection_id", "=", remote_connection_id],
                        ["remote_id", "=", move.id],
                    ]
                    remote_move_ids = models_proxy.execute_kw(
                        self.database_name,
                        uid,
                        self.password,
                        "pos.remote.received.stock.move",
                        "search",
                        [domain_move],
                        {"limit": 1},
                    )
                    move_vals = self._prepare_receiver_stock_move_vals(move, remote_connection_id)
                    if remote_move_ids:
                        models_proxy.execute_kw(
                            self.database_name,
                            uid,
                            self.password,
                            "pos.remote.received.stock.move",
                            "write",
                            [[remote_move_ids[0]], move_vals],
                        )
                    else:
                        models_proxy.execute_kw(
                            self.database_name,
                            uid,
                            self.password,
                            "pos.remote.received.stock.move",
                            "create",
                            [move_vals],
                        )
                    stock_move_sent += 1

        # Llamar al receptor para que cierre las sesiones y genere contabilidad
        try:
            _logger.info("[REMOTE CONNECTOR] Llamando a finalize_sessions en receptor...")
            models_proxy.execute_kw(
                self.database_name,
                uid,
                self.password,
                "pos.remote.sync.connection",
                "action_finalize_sessions",
                [[remote_connection_id]],
                {}
            )
            _logger.info("[REMOTE CONNECTOR] Sesiones finalizadas exitosamente en receptor")
        except Exception as e:
            _logger.warning("[REMOTE CONNECTOR] No se pudieron finalizar sesiones automáticamente: %s", str(e))
            # No fallar el envío completo si esto falla

        return session_sent, order_sent, line_sent, payment_sent, stock_move_sent

    def _find_remote_receiver_connection_id(self, models_proxy, uid):
        domain = [["db_name", "=", self.env.cr.dbname], ["active", "=", True]]
        remote_connection_ids = models_proxy.execute_kw(
            self.database_name,
            uid,
            self.password,
            "pos.remote.sync.connection",
            "search",
            [domain],
            {"limit": 1},
        )
        if not remote_connection_ids:
            raise UserError(
                _(
                    "No hay una conexión activa en la base destino para recibir datos de esta base. "
                    "En la base destino, crea una conexión en POS Sync Remoto > Conexiones con Base de datos remota = %(db)s.",
                    db=self.env.cr.dbname,
                )
            )
        return remote_connection_ids[0]

    def _remote_model_exists(self, models_proxy, uid, model_name):
        return bool(
            models_proxy.execute_kw(
                self.database_name,
                uid,
                self.password,
                "ir.model",
                "search_count",
                [[["model", "=", model_name]]],
            )
        )

    def _get_remote_target_type(self, models_proxy, uid):
        receiver_session_exists = self._remote_model_exists(models_proxy, uid, "pos.remote.received.session")
        receiver_order_exists = self._remote_model_exists(models_proxy, uid, "pos.remote.received.order")
        receiver_line_exists = self._remote_model_exists(models_proxy, uid, "pos.remote.received.order.line")
        receiver_payment_exists = self._remote_model_exists(models_proxy, uid, "pos.remote.received.payment")
        receiver_stock_move_exists = self._remote_model_exists(models_proxy, uid, "pos.remote.received.stock.move")
        if (
            receiver_session_exists
            and receiver_order_exists
            and receiver_line_exists
            and receiver_payment_exists
            and receiver_stock_move_exists
        ):
            return "receiver"
        if (
            receiver_session_exists
            or receiver_order_exists
            or receiver_line_exists
            or receiver_payment_exists
            or receiver_stock_move_exists
        ):
            raise UserError(
                _(
                    "La base destino tiene una instalación incompleta del módulo receptor POS. "
                    "Verifica que existan todos los modelos: pos.remote.received.session, pos.remote.received.order, "
                    "pos.remote.received.order.line, pos.remote.received.payment y pos.remote.received.stock.move."
                )
            )
        return "mirror"

    def _ensure_remote_pos_models(self, models_proxy, uid):
        required_models = [
            "odoo.remote.pos.session",
            "odoo.remote.pos.order",
            "odoo.remote.pos.order.line",
            "odoo.remote.pos.payment",
            "odoo.remote.stock.move",
        ]
        missing_models = []
        for model_name in required_models:
            exists = models_proxy.execute_kw(
                self.database_name,
                uid,
                self.password,
                "ir.model",
                "search_count",
                [[["model", "=", model_name]]],
            )
            if not exists:
                missing_models.append(model_name)

        if missing_models:
            raise UserError(
                _(
                    "Faltan modelos en la base destino: %(models)s. "
                    "Instala o actualiza el módulo odoo_remote_db_connector en la base remota %(db)s e intenta de nuevo.",
                    models=", ".join(missing_models),
                    db=self.database_name,
                )
            )

    def action_send_closed_pos_sessions(self):
        self.ensure_one()
        sessions = self.env["pos.session"].search([("state", "in", ["closing_control", "closed"])])
        if not sessions:
            raise UserError(_("No hay sesiones de punto de venta cerradas para enviar."))

        try:
            session_sent, order_sent, line_sent, payment_sent, stock_move_sent = self.send_pos_sessions(sessions)
        except Exception as error:
            raise UserError(_("No fue posible enviar sesiones POS: %s") % error) from error

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Envío POS completado"),
                "message": _(
                    "Se enviaron %(sessions)s sesiones, %(orders)s pedidos, %(lines)s líneas, %(payments)s pagos y %(moves)s recogidas.",
                    sessions=session_sent,
                    orders=order_sent,
                    lines=line_sent,
                    payments=payment_sent,
                    moves=stock_move_sent,
                ),
                "type": "success",
                "sticky": False,
            },
        }

    @api.constrains("url")
    def _check_url(self):
        for record in self:
            parsed = urlparse((record.url or "").strip())
            if parsed.scheme not in ("http", "https") or not parsed.netloc:
                raise ValidationError(
                    _("La URL debe incluir protocolo y dominio válidos, por ejemplo: https://miempresa.odoo.com")
                )

    def _get_base_url(self):
        self.ensure_one()
        parsed = urlparse((self.url or "").strip())
        return f"{parsed.scheme}://{parsed.netloc}".rstrip("/")

    def _xmlrpc_endpoint(self, service):
        self.ensure_one()
        return "%s/xmlrpc/2/%s" % (self._get_base_url(), service)

    def get_remote_session(self):
        self.ensure_one()
        common_proxy = xmlrpc.client.ServerProxy(self._xmlrpc_endpoint("common"), allow_none=True)
        uid = common_proxy.authenticate(self.database_name, self.username, self.password, {})
        if not uid:
            raise UserError(_("Autenticación inválida. Verifica base de datos, usuario y contraseña."))
        models_proxy = xmlrpc.client.ServerProxy(self._xmlrpc_endpoint("object"), allow_none=True)
        return uid, models_proxy, common_proxy

    def action_test_connection(self):
        self.ensure_one()
        try:
            uid, _models_proxy, common_proxy = self.get_remote_session()

            version_info = common_proxy.version() or {}
            self.write(
                {
                    "state": "connected",
                    "uid": uid,
                    "server_version": version_info.get("server_version", ""),
                    "last_tested_on": fields.Datetime.now(),
                }
            )

            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Conexión exitosa"),
                    "message": _("Conectado correctamente a %(db)s con UID %(uid)s.", db=self.database_name, uid=uid),
                    "type": "success",
                    "sticky": False,
                },
            }
        except Exception as error:
            self.write(
                {
                    "state": "failed",
                    "uid": 0,
                    "server_version": False,
                    "last_tested_on": fields.Datetime.now(),
                }
            )
            raise UserError(_("No fue posible conectarse al Odoo remoto: %s") % error) from error
 