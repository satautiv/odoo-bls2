odoo.define('config_bls_stock.ListRenderer', function (require) {
	"use strict";

	var ListRenderer = require('web.ListRenderer');
	
	
//	Padaryta, kad per veiksmo context'a padavus atributa multi_checkbox - true, poasikeistu checkboxu mechanizmas.
//	Paspaudus ant kazkokio checkboxo lygiai ta pati veiksma (uzdeda arba nuima) padaro ir visiems kitiems zemiau esantiems checkboxams
	
	ListRenderer.include({
	    /**
	     * @private
	     * @param {MouseEvent} event
	     */
	    _onSelectRecord: function (event) {
	        event.stopPropagation();
	        this._updateSelection();
	        
	        var current_target_check_state = $(event.currentTarget).find('input').prop('checked');
	        var table_line = event.currentTarget.parentElement;
	        
	        var context = this.state.context;
	        
	        if (context.hasOwnProperty('multi_checkbox') && context.multi_checkbox == true){
		        var next_line = table_line.nextSibling;
		        var next_line_input;
		        
		        while (next_line) {
			        next_line_input = $(next_line.children[0]).find('input');
			        if (next_line_input.length > 0){
				        next_line_input[0].checked = current_target_check_state;
				        next_line = next_line.nextSibling;
			        } else {
			        	next_line = false;
			        };
		        };
		        this._updateSelection();
	        };
	        
	        if (!current_target_check_state) {
	            this.$('thead .o_list_record_selector input').prop('checked', false);
	        }
	        

	    },
	});
	
});