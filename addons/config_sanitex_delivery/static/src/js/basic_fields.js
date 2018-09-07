odoo.define('config_sanitex_delivey.basic_fields', function (require) {
	"use strict";

    var basic_fields = require('web.basic_fields');
    var core = require('web.core');
    var utils = require('web.utils');
    var Dialog = require('web.Dialog');

    basic_fields.FieldInteger.include({
        _setValue: function (value, options) {
//            if (options && options.disableNegative && value && value < 0) {
//                value = '0';
//            } else if (value && value < 0 && this.hasOwnProperty('attrs') && this.attrs.hasOwnProperty('disable_negative') && this.attrs.disable_negative){
////            var def = $.Deferred();
////            var dialog = Dialog.confirm(this, 'klaida', {
////                title: ("Warning"),
////                confirm_callback: def.resolve.bind(def, true),
////                cancel_callback: def.reject.bind(def),
////            });
////            dialog.on('closed', def, def.reject);
////                value = '0';
////                return this._super(value, options);
//            }
//               this.do_warn('DAR KITOKS ');
            return this._super.apply(this, arguments);
//            var def = $.Deferred();
//            console.log('DEF', def);
//            var dialog = Dialog.confirm(this, 'klaida', {
//                title: ("Warning"),
//                confirm_callback: def.resolve.bind(def, true),
//                cancel_callback: def.reject.bind(def),
//            });
////            alert("KLIASA");
//            dialog.on('closed', def, def.reject);
//            return def;
        }
    })


    basic_fields.FieldFloat.include({
        _setValue: function (value, options) {
            if (options && options.disableNegative && value && value < 0) {
                value = '0';
            } else if (value && value < 0 && this.hasOwnProperty('attrs') && this.attrs.hasOwnProperty('disable_negative') && this.attrs.disable_negative){
                value = '0';
                return this._super(value, options);
            }
            return this._super.apply(this, arguments)
        }
    })


});