odoo.define('config_bls_stock.FormController', function (require) {
	"use strict";
	
	var FormController = require('web.FormController');
	var rpc = require('web.rpc');
    var core = require('web.core');
    var Sidebar = require('web.Sidebar');
    var framework = require('web.framework');

    var _t = core._t;

	FormController.include({
	  //-------- Metodas, kuris formview'e isrenderina mygtukus. Uzklotas pridedant savo mygtuku
	    renderButtons: function() {
	        var self = this;
	        var init_this = this;
//	        var search_view = this.__parentedParent.searchview;
	        
	        this._super.apply(this, arguments); // Sets this.$buttons
	        
	        if (this.hasOwnProperty('$buttons')){
	        
		        var create_invoice_btn = this.$buttons.find("button#button_create_invoice")
		        
		        var active_model = this.modelName;
		        
		        var ctx = this.initialState.context;
		        
		        var create_invoice_objs = {
			        	'sale.order': 'do_invoice',
			        	'stock.route.template': 'do_invoice',
			        }
		        
		      //************************************************************************************************       
		      //******************************** MARSRUTU SUKURIMO MYGTUKAS ************************************
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
	  				            	init_this.do_action(result);
	  				            	
	  				            }, function(type,err){
	  				            	framework.unblockUI();
	  				            	if (err.hasOwnProperty('data') && err.data != 'undefined'){
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
	  	        };
	        };
  	    },
	});

});