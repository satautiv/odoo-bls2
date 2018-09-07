odoo.define('config_sanitex_delivey.ListRenderer', function (require) {
	"use strict";

	var ListRenderer = require('web.ListRenderer');
    var field_utils = require('web.field_utils');
	
	var DECORATIONS = [
	    'decoration-bf',
	    'decoration-it',
	    'decoration-danger',
	    'decoration-info',
	    'decoration-muted',
	    'decoration-primary',
	    'decoration-success',
	    'decoration-warning'
	];

    var FIELD_CLASSES = {
        float: 'o_list_number',
        integer: 'o_list_number',
        monetary: 'o_list_number',
        text: 'o_list_text',
    };
	
	// Nuajas listas su dekoratoriu pavadinimais fono spalvinimui
	var BACKGROUND_DECORATIONS = [
		'background-decoration-success',
		'background-decoration-red',
	]
	//Naujas objiektas, kur skirtingiems dekoratoriams yra galimybe parinkti spalvas
	// jei cia kazkokiam dekoratoriui nera parinktos spalvos, tuomet bus viskas vykdoma pagal standarta
	var background_decorator_colors = {
		'background-decoration-success': '#c7fcc8',
		'background-decoration-red': '#ff9a9a',
	};
	
	ListRenderer.include({
	    init: function (parent, state, params) {
	        this._super.apply(this, arguments);
	        this.hasHandle = false;
	        this.handleField = 'sequence';
	        this._processColumns(params.columnInvisibleFields || {});
	        this.rowDecorations = _.chain(this.arch.attrs)
	            .pick(function (value, key) {
	                return DECORATIONS.indexOf(key) >= 0;
	            }).mapObject(function (value) {
	                return py.parse(py.tokenize(value));
	            }).value();
	        this.hasSelectors = params.hasSelectors;
	        this.selection = [];
	        this.pagers = []; // instantiated pagers (only for grouped lists)
	        this.editable = params.editable;
	        this.rowBackgroundDecorations = _.chain(this.arch.attrs)
	            .pick(function (value, key) {
	                return BACKGROUND_DECORATIONS.indexOf(key) >= 0;
	            }).mapObject(function (value) {
	                return py.parse(py.tokenize(value));
	            }).value();
	    },
		// Decorator spalvinimas
		_setDecorationClasses: function (record, $tr) {
	        _.each(this.rowDecorations, function (expr, decoration) {
	            var cssClass = decoration.replace('decoration', 'text');
	            $tr.toggleClass(cssClass, py.PY_isTrue(py.evaluate(expr, record.evalContext)));
	        });
	        _.each(this.rowBackgroundDecorations, function (expr, decoration) {
        		if (py.PY_isTrue(py.evaluate(expr, record.evalContext)) && background_decorator_colors.hasOwnProperty(decoration)){
	    			$tr[0].style['background-color'] = background_decorator_colors[decoration];
	    		};
	        });
	    },

        // Dėl apvalinimo. Kad skaičius tokius kaip 4.0 rodytų tiesiog 4, 4.1 ir rodytų kaip 4.1
        _renderBodyCell: function (record, node, colIndex, options) {
            var tdClassName = 'o_data_cell';
            if (node.tag === 'button') {
                tdClassName += ' o_list_button';
            } else if (node.tag === 'field') {
                var typeClass = FIELD_CLASSES[this.state.fields[node.attrs.name].type];
                if (typeClass) {
                    tdClassName += (' ' + typeClass);
                }
                if (node.attrs.widget) {
                    tdClassName += (' o_' + node.attrs.widget + '_cell');
                }
            }
            var $td = $('<td>', {class: tdClassName});

            // We register modifiers on the <td> element so that it gets the correct
            // modifiers classes (for styling)
            var modifiers = this._registerModifiers(node, record, $td, _.pick(options, 'mode'));
            // If the invisible modifiers is true, the <td> element is left empty.
            // Indeed, if the modifiers was to change the whole cell would be
            // rerendered anyway.
            if (modifiers.invisible && !(options && options.renderInvisible)) {
                return $td;
            }

            if (node.tag === 'button') {
                return $td.append(this._renderButton(record, node));
            } else if (node.tag === 'widget') {
                return $td.append(this._renderWidget(record, node));
            }
            if (node.attrs.widget || (options && options.renderWidgets)) {
                var widget = this._renderFieldWidget(node, record, _.pick(options, 'mode'));
                this._handleAttributes(widget.$el, node);
                return $td.append(widget.$el);
            }
            var name = node.attrs.name;
            var field = this.state.fields[name];
            var value = record.data[name];
            var formattedValue = field_utils.format[field.type](value, field, {
                data: record.data,
                escape: true,
                isPassword: 'password' in node.attrs,
                toIntWhenPossible: 'int_convert' in node.attrs,
                disableNegative: 'disable_negative' in node.attrs,
                toDashWhenZero: 'zero_to_dash' in node.attrs,
            });
            this._handleAttributes($td, node);
            return $td.html(formattedValue);
        },


	});
	
});