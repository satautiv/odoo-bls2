odoo.define('config_sanitex_delivey.EditableListRenderer', function (require) {
	"use strict";
	
	var ListRenderer  = require('web.ListRenderer');
	
	ListRenderer.include({
		
		
		// Padaryta, kad "nuemus" fokusa nuo redaguojamos eilutes dingtu aktyvios eilutes paspalvinimas
		// (Susijes su metodu zemiau, kuris ir paspalvina aktyvia eilute)
		unselectRow: function () {
	    	if (this.$el.find('table').length == 1){
	        	var table = this.$el.find('table')[0];
	        	if (table.tBodies.length == 1){
	        		var rows = table.tBodies[0].childNodes;
	        		for (var i=0; i < rows.length; i++) {
	    				rows[i].style['background-color'] = '';
	        		}
	        	}
	        }
	    	
	        // Protect against calling this method when no row is selected
	        if (this.currentRow === null) {
	            return $.when();
	        }

	        var record = this.state.data[this.currentRow];
	        var recordWidgets = this.allFieldWidgets[record.id];
	        toggleWidgets(true);

	        var def = $.Deferred();
	        this.trigger_up('save_line', {
	            recordID: record.id,
	            onSuccess: def.resolve.bind(def),
	            onFailure: def.reject.bind(def),
	        });
	        return def.fail(toggleWidgets.bind(null, false));

	        function toggleWidgets(disabled) {
	            _.each(recordWidgets, function (widget) {
	                var $el = widget.getFocusableElement();
	                $el.prop('disabled', disabled);
	            });
	        }
	    },
	    
	    
	    // Padaryta, kad paspalvintu aktyvia redaguojama eilute
	    _selectRow: function (rowIndex) {
	        // Do nothing if already selected
	        if (rowIndex === this.currentRow) {
	            return $.when();
	        }
	        // To select a row, the currently selected one must be unselected first
	        var self = this;
	        return this.unselectRow().then(function () {
	            if (self.state.data.length <= rowIndex) {
	                // The row to selected doesn't exist anymore (probably because
	                // an onchange triggered when unselecting the previous one
	                // removes rows)
	                return $.Deferred().reject();
	            }
	            // Notify the controller we want to make a record editable
	            var def = $.Deferred();
	            
	            if (self.$el.find('table').length == 1){
	            	var table = self.$el.find('table')[0];
	            	if (table.tBodies.length == 1){
	            		var rows = table.tBodies[0].childNodes;
	            		rows[rowIndex].style['background-color'] = '#bbe7ad';
	            	}
	            }
	            
	            self.trigger_up('edit_line', {
	                index: rowIndex,
	                onSuccess: def.resolve.bind(def),
	            });
	            return def;
	        });
	    },
		
	});
	
});