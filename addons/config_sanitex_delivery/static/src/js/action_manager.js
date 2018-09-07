odoo.define('config_sanitex_delivey.ActionManager', function (require) {
	"use strict";
	
	var ActionManager = require('web.ActionManager');
	var core = require('web.core');
	var Widget = require('web.Widget');
	
	ActionManager.include({
		
//----- Formos vaizde jei atidaroma pvz. one2many forma ir is ten paspaudziama, ant kaikokio iraso, tas irasas
// atsidarydavo pagrindiniame lange, bet tas one2many formos vaizdo popupas neuzsidarydavo.
// kodas zemiau padaro, kad tokiais atvejais, tas issokes langas atsijungtu.
	    ir_actions_act_window: function (action, options) {
	    	var modal_node;
	    	var modal_backdrop_node;
	    	
	    	if (this.__parentedParent && this.__parentedParent.$el && this.__parentedParent.$el[0].children){
	    		var parent_children = this.__parentedParent.$el[0].children;
	    		for (var i = 0; i < parent_children.length; i++) {
	    			if (parent_children[i].id && parent_children[i].id.startsWith("modal_")){
	    				modal_node = parent_children[i];
	    			};
	    			if (parent_children[i].classList){
						var class_list = parent_children[i].classList;
						for (var j = 0; j < class_list.length; j++) {
							if (class_list[j] == "modal-backdrop"){
								modal_backdrop_node = parent_children[i];
								break;
							}
						}
	    			};
	    		}
	    	}
	    	if (modal_node && modal_node != undefined){
	    		modal_node.remove();
	    	}
	    	if (modal_backdrop_node && modal_backdrop_node != undefined){
	    		modal_backdrop_node.remove();
	    	}
	    	
	    	return this._super(action, options);
	    },
	    
	//Perklotas client actionas ir padaryta, kad gavus tag'a breadcrumb_back, griztu 1u langu atgal
		ir_actions_client: function (action, options) {
	        var self = this;
	        
	        if (action.tag == 'breadcrumb_back'){
	        	var breadcrumbs = this.get_breadcrumbs();
	        	if (breadcrumbs.length > 1){
	        		var previuous_breadcrumb = breadcrumbs[breadcrumbs.length - 2]
	        		this.select_action(previuous_breadcrumb.action, previuous_breadcrumb.index);
	        	}else{
	        		this.do_action({
                        type: "ir.actions.client",
                        tag: 'reload',
                    });
	        	}
	        	return
	        }
	        
	        var ClientWidget = core.action_registry.get(action.tag);
	        if (!ClientWidget) {
	            return self.do_warn("Action Error", "Could not find client action '" + action.tag + "'.");
	        }
	        if (!(ClientWidget.prototype instanceof Widget)) {
	            var next;
	            if ((next = ClientWidget(this, action))) {
	                return this.do_action(next, options);
	            }
	            return $.when();
	        }

	        return this.ir_actions_common({
	            widget: function () {
	                return new ClientWidget(self, action, options);
	            },
	            action: action,
	            klass: 'oe_act_client',
	        }, options).then(function () {
	            if (action.tag !== 'reload') {self.do_push_state({});}
	        });
	    },
		
	});
	
	
	
});