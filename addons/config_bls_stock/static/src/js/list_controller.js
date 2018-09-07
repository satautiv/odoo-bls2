odoo.define('config_bls_stock.ListView', function (require) {
	"use strict";
	
	var ListView = require('web.ListView');
	
	var Session = require('web.session');

	var search_inputs = require('web.search_inputs');
	var ListRender  = require('web.ListRenderer');
	
	var ListController  = require('web.ListController');
	var rpc = require('web.rpc');
	
	var config = require('web.config');
	var field_utils = require('web.field_utils');
	
	var framework = require('web.framework');
	
	ListController.include({
		
//-------- Metodas, kuris listview'e isrenderina mygtukus. Uzklotas pridedant savo mygtuku
		renderButtons: function() {
	        var self = this;
	        
	        var init_this = this;
//	        var search_view = this.__parentedParent.searchview;
	        
	        this._super.apply(this, arguments); // Sets this.$buttons
	        
	        var this_super = this._super;
	        var args = arguments;

	        var create_invoice_btn = this.$buttons.find("button#button_create_invoice");
	        var create_invoice_btn_separator = this.$buttons.find("span#invoice_create_vertical_separator");
	        
	        var active_model = this.modelName;
	        
	        var ctx = this.initialState.context;       
	        
	       var create_invoice_objs = {
	        	'sale.order': 'do_invoice',
	        	'stock.route.template': 'do_invoice',
	        }

//************************************************************************************************       
//******************************** INVOICE SUKURIMO MYGTUKAS ************************************
//************************************************************************************************
	        if (ctx.hasOwnProperty('create_invoice_btn') && ctx.create_invoice_btn == true){
	            if (create_invoice_btn.length > 0 && typeof(create_invoice_btn[0]) != 'undefined' && create_invoice_btn[0] != null){
	            	create_invoice_btn[0].style.display = 'inline-block';
	            	create_invoice_btn[0].style.position = 'relative';
	            };
	            create_invoice_btn.on('click', function (event) {
		        	var selected_ids = init_this.getSelectedIds();
		        	if (selected_ids.length > 0){
		        		framework.blockUI();
			        	rpc.query({
				                model: active_model,
				                method: create_invoice_objs[active_model],
				                args: [selected_ids],
				            }, {
				                timeout: 1200000,
				                shadow: true,
				            })
				            .then(function(result){
				            	framework.unblockUI();
				        		var search_view = self.getParent().searchview;
				        		search_view.query.trigger('reset');
//				        		console.log("----res: ", res);
//				        		init_this.do_action(result);
				            	setTimeout(function() {init_this.do_action(result)}, 2000);
				            }, function(type,err){
				            	framework.unblockUI();
				            	if (err.hasOwnProperty('data')){
  				            		alert(err.data.message);
  				            	}else if (err.hasOwnProperty('statusText')){
  				            		alert(err.statusText);
  				            	}
				            }
			            );
		        	}
		        	
	            });
	            
	        }else{
	            if (create_invoice_btn.length > 0 && typeof(create_invoice_btn[0]) != 'undefined' && create_invoice_btn[0] != null){
	            	create_invoice_btn.hide();
	            };
	            if (create_invoice_btn_separator.length > 0 && typeof(create_invoice_btn_separator[0]) != 'undefined' && create_invoice_btn_separator[0] != null){
	            	create_invoice_btn_separator.hide();
	            };
	        }; 

	        
//----- RENDER BUTTONS metodo pabaiga	        
	    }
	
	});
	
});