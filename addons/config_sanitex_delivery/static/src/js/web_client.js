odoo.define('config_sanitex_delivey.WebClient', function (require) {
	"use strict";
	
	var AbstractWebClient  = require('web.AbstractWebClient');
	var mixins = require('web.mixins');
	var concurrency = require('web.concurrency');
	
// Pagal kliento reikalavima, padaryta, kad narsykles TAB'u pavadinime, visur vietoj 'Odoo' rasytu 'Atlas'
	AbstractWebClient.include({
		init: function (parent) {
	        this.client_options = {};
	        mixins.ServiceProvider.init.call(this);
	        this._super(parent);
	        this.origin = undefined;
	        this._current_state = null;
	        this.menu_dm = new concurrency.DropMisordered();
	        this.action_mutex = new concurrency.Mutex();
	        this.set('title_part', {"zopenerp": "Atlas"});
	    }
	});
});