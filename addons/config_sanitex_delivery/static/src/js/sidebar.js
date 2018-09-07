odoo.define('config_sanitex_delivey.Sidebar', function (require) {
	"use strict";
	
	var Sidebar  = require('web.Sidebar');
	var core = require('web.core');
	var rpc = require('web.rpc');
	
	var QWeb = core.qweb;
	
	// Uzklota, kad butu galima paslepti PRINT mygtukus, pagal poreiki
	Sidebar.include({
		_redraw: function () {
	        this.$el.html(QWeb.render('Sidebar', {widget: this}));
	        var active_ids = this.env.activeIds;
	        var context = this.env.context;
	        var active_model = this.env.model;
	        if (
	        	this.$('.o_dropdown').length == 2 &&
	        	context && context != undefined &&
	        	context.hasOwnProperty('hide_print_button') &&
	        	context.hide_print_button == true
	        ){
        		var print_dropdown_element = this.$('.o_dropdown')[0];
        		
        		rpc.query({
		                model: active_model,
		                method: 'show_print_button',
		                args: [active_ids, context],
		            }, {
		                timeout: 5000,
		                shadow: true,
		            })
		            .then(function(result){
	    	    		if (result){
	    	    			$(print_dropdown_element).show();
	    	    		} else {
	    	    			$(print_dropdown_element).hide();
	    	    		};
		            }, function(type,err){
		            	$(print_dropdown_element).hide();
		            }
	            );
	        	
	        };
	        
	        // Hides Sidebar sections when item list is empty
	        this.$('.o_dropdown').each(function () {
	            if (!$(this).find('li').length) {
	                $(this).hide();
	            }
	        });
	        this.$("[title]").tooltip({
	            delay: { show: 500, hide: 0}
	        });
	    },


	// Veiksmo mygtukai surikiuojami pagal sequence numerį
	    _addToolbarActions: function (toolbarActions) {
            var self = this;
            _.each(['print','action','relate'], function (type) {
                if (type in toolbarActions) {
                    var actions = toolbarActions[type];
                    if (actions && actions.length) {

                        var items = _.map(actions, function (action) {
                            return {
                                label: action.name,
                                action: action,
                                sequence_no: action.hasOwnProperty('sequence_no') ? action['sequence_no'] : 100
                            };
                        });
                        self._addItems(type === 'print' ? 'print' : 'other', items);
                    }
                }
            });
            if ('other' in toolbarActions) {
                this._addItems('other', toolbarActions.other);
                this.items['other'].sort(function(obj1, obj2) {
                    return obj1.sequence_no - obj2.sequence_no;
                });
            }
        },
	});
	
});