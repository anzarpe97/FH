odoo.define('pos_features_in_one.PosSessionReport', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const ProductScreen = require('point_of_sale.ProductScreen');
    const Registries = require('point_of_sale.Registries');
    const { useListener } = require("@web/core/utils/hooks");
    const { ConnectionLostError, ConnectionAbortedError} = require('@web/core/network/rpc_service')

    class SessionReport extends PosComponent {
        setup() {
            super.setup();
            useListener('click', this.onClick);
        }
        async onClick() {
            await this.env.legacyActionManager.do_action('pos_features_in_one.action_report_session_z', {
                additional_context: {
                    active_ids: [this.env.pos.pos_session.id],
                },
            });
        }
    }
    SessionReport.template = 'SessionReport';

    ProductScreen.addControlButton({
        component: SessionReport,
        condition: function() {
            return this.env.pos.config.pos_session_report;
        },
    });

    Registries.Component.add(SessionReport);

    return SessionReport;
});
