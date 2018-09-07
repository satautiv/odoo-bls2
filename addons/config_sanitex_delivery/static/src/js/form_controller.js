odoo.define('config_sanitex_delivey.FormController', function (require) {
	"use strict";
	
	var FormController = require('web.FormController');
	var rpc = require('web.rpc');
    var core = require('web.core');
    var Sidebar = require('web.Sidebar');

    var _t = core._t;

	FormController.include({
	// Jei context'e yra reiksme end_edit_mode_states (listas) ir aktyvus irasas yra redaguojas, o jo
	// busena yra context'o atributo sarase, tada tokiam irasui nutraukiamas redagavimas
		_update: function () {
	        var title = this.getTitle();
	        this.set('title', title);
	        this._updateButtons();
	        this._updateSidebar();
	        
	        var res = this._super.apply(this, arguments).then(this.autofocus.bind(this));

	        if (this.mode === 'edit' && this.hasOwnProperty('renderer') && this.renderer.hasOwnProperty('state') && this.renderer.state.hasOwnProperty('data')){
	        	var state = this.renderer.state.data.state;
	        	var ctx = this.initialState.context;
	        		
//	        	this.renderer._renderView();

	        	if (ctx.hasOwnProperty('end_edit_mode_states') && ctx.end_edit_mode_states.includes(state)){
	        		this._setMode('readonly');
	        	}
	        };
	        
	        return res;
	    },
	    
    // Jei context'e yra reiksme hide_save_button (true), tada paslepiamas SAVE mygtukas
	// Jei context'e yra reiksme hide_cancel_button (true), tada paslepiamas CANCEL mygtukas
	    _updateButtons: function () {
	        if (this.$buttons) {
	            if (this.footerToButtons) {
	                var $footer = this.$('footer');
	                if ($footer.length) {
	                    this.$buttons.empty().append($footer);
	                }
	            }
	            var edit_mode = (this.mode === 'edit');
	            this.$buttons.find('.o_form_buttons_edit')
	                         .toggleClass('o_hidden', !edit_mode);
	            this.$buttons.find('.o_form_buttons_view')
	                         .toggleClass('o_hidden', edit_mode);
	            
	            if (edit_mode && this.$buttons.find('.o_form_button_save').length == 1){
	            	var save_button = this.$buttons.find('.o_form_button_save')[0];
	            	var ctx = this.initialState.context;
	            	if (ctx.hasOwnProperty('hide_save_button') && ctx['hide_save_button']){
	            		$(save_button).hide();
	            	};
	            }
	            if (edit_mode && this.$buttons.find('.o_form_button_cancel').length == 1){
	            	var cancel_button = this.$buttons.find('.o_form_button_cancel')[0];
	            	var ctx = this.initialState.context;
	            	if (ctx.hasOwnProperty('hide_cancel_button') && ctx['hide_cancel_button']){
	            		$(cancel_button).hide();
	            	};
	            }
	        }
	    },
	    
	    
	    
	  //-------- Metodas, kuris formview'e isrenderina mygtukus. Uzklotas pridedant savo mygtuku
	    renderButtons: function() {
	        var self = this;
	        
	        var init_this = this;
//	        var search_view = this.__parentedParent.searchview;
	        
	        this._super.apply(this, arguments); // Sets this.$buttons
	        
	        if (this.hasOwnProperty('$buttons')){
	        
		        var create_route_btn = this.$buttons.find("button#button_crate_route")
		        
		        var active_model = this.modelName;
		        
		        var ctx = this.initialState.context;
		        
		        var create_route_objs = {
		        	'sale.order': 'action_create_route_confirm',
		        	'stock.route.template': 'action_create_route_confirm',
		        }
		        
		      //************************************************************************************************       
		      //******************************** MARSRUTU SUKURIMO MYGTUKAS ************************************
		      //************************************************************************************************
	  	        if (ctx.hasOwnProperty('create_route_btn') && ctx.create_route_btn == true){
	  	            if (create_route_btn.length > 0 && typeof(create_route_btn[0]) != 'undefined' && create_route_btn[0] != null){
	  	            	create_route_btn[0].style.display = 'inline-block';
	  	            	create_route_btn[0].style.position = 'relative';
	  	            };
	  	            create_route_btn.on('click', function (event) {
	  		        	var selected_ids = init_this.getSelectedIds();
	  		        	if (selected_ids.length > 0){
	  			        	rpc.query({
	  				                model: active_model,
	  				                method: create_route_objs[active_model],
	  				                args: [selected_ids],
	  				            }, {
	  				                timeout: 5000,
	  				                shadow: true,
	  				            })
	  				            .then(function(result){
	  				            	init_this.do_action(result);
	  				            	
	  				            }, function(type,err){
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
	  	            if (create_route_btn.length > 0 && typeof(create_route_btn[0]) != 'undefined' && create_route_btn[0] != null){
	  	            	create_route_btn.hide();
	  	            };
	  	        };
	        };
  	    },


	// Veiksmo mygtukams pridedami sequence numeriai, kad vėliau būtų galima surykiuoti mygtukus
        renderSidebar: function ($node) {
            if (!this.sidebar && this.hasSidebar) {
                var otherItems = [];
                if (this.is_action_enabled('delete')) {
                    otherItems.push({
                        label: _t('Delete'),
                        callback: this._onDeleteRecord.bind(this),
                        sequence_no: 80
                    });
                }
                if (this.is_action_enabled('create') && this.is_action_enabled('duplicate')) {
                    otherItems.push({
                        label: _t('Duplicate'),
                        callback: this._onDuplicateRecord.bind(this),
                        sequence_no: 70
                    });
                }
                this.sidebar = new Sidebar(this, {
                    editable: this.is_action_enabled('edit'),
                    viewType: 'form',
                    env: {
                        context: this.model.get(this.handle).getContext(),
                        activeIds: this.getSelectedIds(),
                        model: this.modelName,
                    },
                    actions: _.extend(this.toolbarActions, {other: otherItems}),
                });
                this.sidebar.appendTo($node);

                // Show or hide the sidebar according to the view mode
                this._updateSidebar();
            }
        },
	    
	});
	
});