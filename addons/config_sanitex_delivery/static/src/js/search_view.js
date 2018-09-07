odoo.define('config_sanitex_delivey.SearchView', function (require) {
	"use strict";
	
	var SearchView  = require('web.SearchView');
	
	SearchView.include({
		
		//Uzklota, kad nuo pradziu pasileistu 'toggle_buttons' ir rodytu search'o mygtukus
		init: function (parent, dataset, fvg, options) {
	        this._super.apply(this, arguments);
	        this.options = options;
	        this.dataset = dataset;
	        this.fields_view = fvg;
	        this.fields = this.fields_view.fields;
	        this.query = undefined;
	        this.title = this.options.action && this.options.action.name;
	        this.action_id = this.options.action && this.options.action.id;
	        this.search_fields = [];
	        this.filters = [];
	        this.groupbys = [];
	        var visibleSearchMenu = this.call('local_storage', 'getItem', 'visible_search_menu');
	        this.visible_filters = (visibleSearchMenu === 'true');
	        this.input_subviews = []; // for user input in searchbar
	        this.search_defaults = this.options.search_defaults || {};
	        this.headless = this.options.hidden &&  _.isEmpty(this.search_defaults);
	        this.$buttons = this.options.$buttons;

	        this.filter_menu = undefined;
	        this.groupby_menu = undefined;
	        this.favorite_menu = undefined;
	        
	        this.toggle_buttons();
	    },
	    
	    //Uzklota, ka dvisada searcho mygtukai butu isskleisti
	    toggle_buttons: function (is_visible) {
	        this.visible_filters = true;
	        if (this.$buttons)  {
	            this.$buttons.toggle(true);
	        }
	    },
	    
	});
});