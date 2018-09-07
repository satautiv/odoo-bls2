odoo.define('config_sanitex_delivey.search_filters', function (require) {
	"use strict";


var core = require('web.core');

console.log('ZOZO', core.search_filters_registry.get('char'))
core.search_filters_registry.get('char').include({

    get_domain: function (field, operator) {
        switch (operator.value) {
        case '∃': return ['|',[field.name, '!=', false],[field.name, '!=', '']]
        case '∄': return ['|',[field.name, '=', false],[field.name, '=', '']];
        default: return [[field.name, operator.value, this.get_value()]];
        }
    },
})

})