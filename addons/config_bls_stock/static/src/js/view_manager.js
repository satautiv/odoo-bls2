odoo.define('config_bls_stock.ViewManager', function (require) {
	"use strict";
	
	var ViewManager = require('web.ViewManager');
	
	ViewManager.include({

//		Uzklota, kad actione butu galima nurodyti, kokios busenos langa atidaryti (edit ar readonly)
		create_view: function(view_descr, view_options) {
	        var self = this;
	        var arch = view_descr.fields_view.arch;
	        var View = this.registry.get(arch.attrs.js_class || view_descr.type);
	        var params = _.extend({}, view_options, {userContext: this.getSession().user_context});
	        
	        if (view_descr.type === "form" && ((this.action.target === 'new' || this.action.target === 'inline' || this.action.target === 'fullscreen') ||
	            (view_options && (view_options.mode === 'edit' || view_options.context.form_view_initial_mode)))) {
	            params.mode = view_options.context.form_view_initial_mode || params.initial_mode || 'edit';
	        }
	       
	        view_descr.searchview_hidden = View.prototype.searchview_hidden;
	        var view = new View(view_descr.fields_view, params);
	        return view.getController(this).then(function(controller) {
	            controller.on('history_back', this, function() {
	                if (self.action_manager) self.action_manager.trigger('history_back');
	            });
	            controller.on("change:title", this, function() {
	                if (self.action_manager && !self.flags.headless) {
	                    var breadcrumbs = self.action_manager.get_breadcrumbs();
	                    self.update_control_panel({breadcrumbs: breadcrumbs}, {clear: false});
	                }
	            });
	            return controller;
	        });
	    },
	});
	
});