# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError
import odoo.addons.decimal_precision as dp


class PosConfig(models.Model):
    _inherit = 'pos.config'

    @api.depends('simplified_invoice_sequence_id.number_next_actual',
                 'simplified_invoice_sequence_id.prefix',
                 'simplified_invoice_sequence_id.padding')
    def _compute_simplified_invoice_sequence(self):
        for pos in self:
            pos.simple_invoice_number =\
                pos.simplified_invoice_sequence_id.number_next_actual
            pos.simple_invoice_prefix =\
                pos.simplified_invoice_sequence_id._get_prefix_suffix()[0]
            pos.simple_invoice_padding =\
                pos.simplified_invoice_sequence_id.padding

    iface_simplified_invoice = fields.Boolean(
        string='Use simplified invoices for this POS',
    )
    simplified_invoice_sequence_id = fields.Many2one(
        'ir.sequence',
        string='Simplified Invoice IDs Sequence',
        help="Autogenerate for each POS created",
        copy=False,
        readonly=True,
    )
    simplified_invoice_limit = fields.Float(
        string='Sim.Inv limit amount',
        digits=dp.get_precision('Account'),
        help='Over this amount is not legally posible to create '
             'a simplified invoice',
        default=3000,  # Spanish leg. limit
    )
    simple_invoice_prefix = fields.Char(
        'Simplified Invoice prefix',
        readonly=True,
        compute='_compute_simplified_invoice_sequence',
    )
    simple_invoice_padding = fields.Integer(
        'Simplified Invoice padding',
        readonly=True,
        compute='_compute_simplified_invoice_sequence',
    )
    simple_invoice_number = fields.Integer(
        'Sim.Inv number',
        readonly=True,
        compute='_compute_simplified_invoice_sequence',
    )

    @api.model
    def create(self, vals):
        # Auto create simp. inv. sequence
        prefix = "%s%s" % (vals['name'], self._get_default_prefix())
        if not self._context.get('copy'):
            self._check_simple_inv_prefix(prefix)
        simp_inv_seq_id = self.env['ir.sequence'].create({
            'name': _('Simplified Invoice %s') % vals['name'],
            'padding': self._get_default_padding(),
            'prefix': prefix,
            'code': 'pos.config.simplified_invoice',
            'company_id': vals.get('company_id', False),
        })
        vals['simplified_invoice_sequence_id'] = simp_inv_seq_id.id
        return super(PosConfig, self).create(vals)

    def copy(self, default=None):
        ctx = dict(self._context)
        ctx.update(copy=True)
        return super(PosConfig, self.with_context(ctx)).copy(default)

    def write(self, vals):
        if 'name' in vals:
            prefix = self.simple_invoice_prefix.replace(
                self.name, vals['name'])
            if prefix != self.simple_invoice_prefix:
                self._check_simple_inv_prefix(prefix)
                self.simplified_invoice_sequence_id.update({
                    'prefix': prefix,
                    'name': self.simplified_invoice_sequence_id.name.replace(
                        self.name, vals['name'])
                })
        if not self._context.get('copy') and 'name' not in vals:
            prefix = "%s%s" % (self.name, self._get_default_prefix())
            self._check_simple_inv_prefix(prefix, 1)
        return super(PosConfig, self).write(vals)

    def unlink(self):
        self.mapped('simplified_invoice_sequence_id').unlink()
        return super(PosConfig, self).unlink()

    def _get_default_padding(self):
        return self.env['ir.config_parameter'].get_param(
            'pos.simp_inv_seq.padding', 4)

    def _get_default_prefix(self):
        return self.env['ir.config_parameter'].get_param(
            'pos.simp_inv_seq.prefix', '')

    def _check_simple_inv_prefix(self, prefix, count=0):
        if not prefix:
            return
        if self.env['ir.sequence'].search_count([
                ('code', '=', 'pos.config.simplified_invoice'),
                ('prefix', '=', prefix)]) > count:
            raise UserError(_(
                "There's already another POS config using the same "
                "Simplified Invoice prefix. Try choosing another POS Name"))

    def set_next_simple_invoice_number(self, order_number):
        # Fix generated orders with empty simplified invoice prefix
        if 'false' in order_number:
            order_number = order_number.replace('false',
                                                self.simple_invoice_prefix)
        number = int(order_number.replace(self.simple_invoice_prefix, ''))
        if number > self.simple_invoice_number:
            self.simplified_invoice_sequence_id.write({
                'number_next_actual': number,
            })
