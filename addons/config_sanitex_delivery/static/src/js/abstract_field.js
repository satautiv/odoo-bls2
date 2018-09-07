odoo.define('config_sanitex_delivey.AbstractField', function (require) {
	"use strict";
	
	var AbstractField  = require('web.AbstractField');
	
	AbstractField.include({
		
		// Uzklota, kad redaguojamame sarase per langelius vaikstant su klaviatura ir iejus i langeli,
		// kuriame yra 0, nerodytu langelio vertes. Taip bus galima vestis skaicius isvengiant tokiu bugu,
		// kaip kad vedant 1 jau esant nuliui, gaunasi 10.
		activate: function (options) {
	        if (this.isFocusable()) {
	            var $focusable = this.getFocusableElement();
	            $focusable.focus();
	            if ($focusable.is('input[type="text"], textarea')) {
	                $focusable[0].selectionStart = $focusable[0].selectionEnd = $focusable[0].value.length;
	                
	                if (options && !options.noselect) {
	                	var numeric_formats = ['integer','float','decimal']
	                
	                	
	                	if (this.formatType && numeric_formats.includes(this.formatType) && this.value == 0 && options.event == undefined){
	                		this.$input.val("");
	                	} else {
	                		$focusable.select();
	                	}
	                	
	                }
	            }
	            return true;
	        }
	        return false;
	    },

        _onKeydown: function (ev) {
            switch (ev.which) {
                case $.ui.keyCode.TAB:
                    ev.preventDefault();
                    ev.stopPropagation();
                    this.trigger_up('navigation_move', {
                        direction: ev.shiftKey ? 'previous' : 'next',
                    });
                    break;
                case $.ui.keyCode.ENTER:
                    ev.stopPropagation();
                    if (
                        this.hasOwnProperty('model')
                        && this.hasOwnProperty('name')
                        && this.model == 'stock.route.document.check_up.osv'
                        && this.name == 'document_number'
                    ){
                        $('button[name="check"]').trigger('click');
                    } else {
                        this.trigger_up('navigation_move', {direction: 'next_line'});
                    }
                    break;
                case $.ui.keyCode.ESCAPE:
                    this.trigger_up('navigation_move', {direction: 'cancel', originalEvent: ev});
                    break;
                case $.ui.keyCode.UP:
                    ev.stopPropagation();
                    this.trigger_up('navigation_move', {direction: 'up'});
                    break;
                case $.ui.keyCode.RIGHT:
                    ev.stopPropagation();
                    this.trigger_up('navigation_move', {direction: 'right'});
                    break;
                case $.ui.keyCode.DOWN:
                    ev.stopPropagation();
                    this.trigger_up('navigation_move', {direction: 'down'});
                    break;
                case $.ui.keyCode.LEFT:
                    ev.stopPropagation();
                    this.trigger_up('navigation_move', {direction: 'left'});
                    break;
            }
        },

	});
	
});