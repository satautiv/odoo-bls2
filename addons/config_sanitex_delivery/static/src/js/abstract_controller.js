odoo.define('config_sanitex_delivey.AbstractController', function (require) {
	"use strict";

	var AbstractController  = require('web.AbstractController');
	var rpc = require('web.rpc');

	AbstractController.include({

		//Padaryta galimybė išimti eksporto mygtuką
		is_action_enabled: function (action) {
            if (action == 'export'){
                var env =this._getSidebarEnv()
                var context = this._getSidebarEnv().context
        		if (context.hasOwnProperty('disable_export')){
        		    return false;
        		} else {
        		    return true;
        		};
	        } else {
                return this.activeActions[action];
            };
        },
	});

});