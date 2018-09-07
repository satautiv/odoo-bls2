odoo.define('config_sanitex_delivey.field_utils', function (require) {
	"use strict";

    var field_utils = require('web.field_utils');
    var core = require('web.core');
    var utils = require('web.utils');

    field_utils.format.float = function (value, field, options) {
        if (value === false) {
            return "";
        } else if (options && options.toIntWhenPossible && value == Math.round(value)){
            return value;
        }
        var l10n = core._t.database.parameters;
        var precision;
        if (value == Math.round(value)){
            return value
        }
        else if (options && options.digits) {
            precision = options.digits[1];
        } else if (field && field.digits) {
            precision = field.digits[1];
        } else {
            precision = 2;
        }
        var formatted = _.str.sprintf('%.' + precision + 'f', value || 0).split('.');
        formatted[0] = utils.insert_thousand_seps(formatted[0]);
        while (formatted[1].slice(-1) == '0'){
            formatted[1] = formatted[1].slice(0, -1)
        }
        return formatted.join(l10n.decimal_point);
    }

    field_utils.format.integer = function (value, field, options) {
        if (options && options.isPassword) {
            return _.str.repeat('*', String(value).length);
        }
        if (!value && value !== 0) {
            // previously, it returned 'false'. I don't know why.  But for the Pivot
            // view, I want to display the concept of 'no value' with an empty
            // string.
            return "";
        }
        if (options && options.toDashWhenZero && value == 0){
            return "-"
        }
        return utils.insert_thousand_seps(_.str.sprintf('%d', value));
    }

});