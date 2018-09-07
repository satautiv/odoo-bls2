odoo.define('config_sanitex_delivey.ListView', function (require) {
	"use strict";
	
	var ListView = require('web.ListView');
	
	var Session = require('web.session');

	var search_inputs = require('web.search_inputs');
	var ListRender  = require('web.ListRenderer');
	
	var ListController  = require('web.ListController');
	var rpc = require('web.rpc');
	
	var config = require('web.config');
	var field_utils = require('web.field_utils');
	
	ListController.include({
		
//-------- Metodas, kuris listview'e isrenderina mygtukus. Uzklotas pridedant savo mygtuku
		renderButtons: function() {
	        var self = this;
	        
	        var init_this = this;
//	        var search_view = this.__parentedParent.searchview;
	        
	        this._super.apply(this, arguments); // Sets this.$buttons
	        
	        var this_super = this._super;
	        var args = arguments;
	        
	        var route_filter_dropdown = this.$buttons.find("span#button_route_filter.dropdown");
	        var owner_filter_dropdown = this.$buttons.find("span#button_owner_filter.dropdown");
	        var shipping_warehouse_filter_dropdown = this.$buttons.find("span#button_shipping_warehouse_filter.dropdown");
	        var date_filter_dropdown = this.$buttons.find("span#button_date_filter.dropdown");
	        var date_from_filter_dropdown = this.$buttons.find("span#button_date_from_filter.dropdown");
	        var date_to_filter_dropdown = this.$buttons.find("span#button_date_to_filter.dropdown");
	        var create_route_btn = this.$buttons.find("button#button_crate_route");
	        var create_route_btn_separator = this.$buttons.find("span#route_create_vertical_separator");

	        var close_routes_btn = this.$buttons.find("button#button_close_routes");
	        var close_routes_btn_separator = this.$buttons.find("span#close_routes_vertical_separator");
	        var framework = require('web.framework');

	        var active_model = this.modelName;
	        
	        var ctx = this.initialState.context;

//	        var owner_filter_objs = ['sale.order','stock.package.document','account.invoice.container']
	        var owner_filter_objs = ['stock.package.document'] //Jei ne visiems objiekto vaizdams reikia, tada dar galima prideti per actiono contexta "show_owner_filter"
	        
	        var date_filter_objs = {
	        	'stock.route.template': 'date',	
	        	'sale.order': 'shipping_date',
	        }
	        
	        var shipping_warehouse_filter_objs = {
	        	'stock.route.template': {
	        		'field_name': 'shipping_warehouses_recalc',
	        		'field_type': 'str'
	        	},	
	        	'sale.order': {
	        		'field_name': 'shipping_warehouse_id',
	        		'field_type': 'id'
	        	}
	        }
	        
	       var create_route_objs = {
	        	'sale.order': 'action_create_route_confirm',
	        	'stock.route.template': 'action_create_route_confirm',
	        }

	       var close_routes_objs = {
	        	'stock.route': 'action_close_multiple_routes',
	        }

	       var date_from_to_filter_objs = {
	        	'account.invoice': 'date_invoice',
	       }

	        
	        
//************************************************************************************************       
//******************************** MARSRUTU FILTRAS **********************************************
//************************************************************************************************
	       
	        if (active_model == 'sale.order'){
	            if (typeof(route_filter_dropdown[0]) != 'undefined' && route_filter_dropdown[0] != null){
	            	route_filter_dropdown[0].style.display = 'inline-block';
	            	route_filter_dropdown[0].style.position = 'relative';
	            };

	        	
	        	route_filter_dropdown.on('click', function (event) {
	        		
		        	if (event.target && event.target.nodeName == "BUTTON"){
		        		var this_parent = init_this.getParent();
		        		var search_view = this_parent.searchview;
			            var search_data = search_view.build_search_data();
			            var action = this_parent.action;
			            var action_domain = action.domain;
			            var action_context = action.context;
			            
		        		if (event.target.id == "button_open_route_filter"){
			        		self = this;
			        		rpc.query({
					                model: 'sale.order',
					                method: 'get_avail_route_numbers',
					                args: [false, search_data.domains, action_domain, action_context],
					            }, {
					                timeout: 5000,
					                shadow: true,
					            })
					            .then(function(result){
				    	    		init_this.route_numbers = result;
				    	    		var route_filter_dropdown_html = '<li ><input type="checkbox" value="" />Empty</li><hr/>'
				    	    		for (var i=0; i < result.length; i++) { 
				    	    			route_filter_dropdown_html += '<li><input type="checkbox" value="'+result[i]+'" />'+result[i]+'</li>'
				    	    		}

				    	    		var dropdown_container = $(self)[0].children[1];
				    	    		var dropdown_container_list = dropdown_container.children[1];
				    	    		
				    	    		dropdown_container_list.innerHTML = route_filter_dropdown_html;
				    	    		
					            }, function(type,err){}
				            );

		        		}else if (event.target.id == "accept_filter") {
		        			self = this;
		        			
		        			var route_numbers = $(self).find('li');
		        			var route_filters = []
		        			for (var i=0; i < route_numbers.length; i++) { 
		        				if (route_numbers[i].nodeName != 'LI'){
		        					continue;
		        				}
		        				
		        				if (route_numbers[i].firstElementChild.checked == true){
		        			        var new_attr = {};
		        			        var route_no = route_numbers[i].children[0].value;
		        			        new_attr.tag = 'filter';
		        			        new_attr.children=[];
		        			        new_attr.attrs = {};
		        			        if (route_no){
			        			        new_attr.attrs.domain = [['route_number','=',route_no]];
			        			        new_attr.attrs.string = "Route Number is "+route_no;
		        			        } else {
			        			        new_attr.attrs.domain = [['route_number','=',false]];
			        			        new_attr.attrs.string = "Route Number is empty";
		        			        }
		        			        route_filters.push(new_attr);
		        				};
		        			};
		        	        var  filters_widgets = _.map(route_filters, function (filter) {
		                        return new search_inputs.Filter(filter, this);
		                    });
		        	        var filter_group = new search_inputs.FilterGroup(filters_widgets, search_view),
		                    facets = filters_widgets.map(function (filter) {
		                        return filter_group.make_facet([filter_group.make_value(filter)]);
		                    });
		        	        
		        	        filter_group.insertBefore(this.$add_filter);
		        	        $('<li class="divider">').insertBefore(this.$add_filter);
		        	        search_view.query.add(facets, {silent: true});
		        	        search_view.query.trigger('reset');

		        		};
		        		
		        		var childs = self.parentNode.children;
			    		var childs_obj = $(childs);
			    		childs_obj.each(function () {
			    			var class_list = this.classList;
			    			if (class_list.contains('dropdown') && class_list.contains('open') && this != self){
			    				$(this).toggleClass('open');
			    			};
				        });
		        		$(self).toggleClass('open');
		        	} // jei prireiktu to elif'o apacioje, sita nutrinti
//		        	}else if (event.target && event.target.nodeName == "INPUT"){
//		        		console.log("event.target: ", event.target);
//		        	};
		        	
		        });
	        }else{
	            if (typeof(route_filter_dropdown[0]) != 'undefined' && route_filter_dropdown[0] != null){
		        	route_filter_dropdown[0].hidden = true;
	            };
	        }; 
	        
	        
	        
	        
	        
	        
//************************************************************************************************       
//******************************** SAVININKU FILTRAS *********************************************
//************************************************************************************************
	        	
	        if (owner_filter_objs.includes(active_model) || (ctx.hasOwnProperty('show_owner_filter') && ctx.show_owner_filter == true)){
	            if (typeof(owner_filter_dropdown[0]) != 'undefined' && owner_filter_dropdown[0] != null){
	            	owner_filter_dropdown[0].style.display = 'inline-block';
	            	owner_filter_dropdown[0].style.position = 'relative';
	            };
	        	owner_filter_dropdown.on('click', function (event) {
		        	if (event.target && event.target.nodeName == "BUTTON"){
		        		var this_parent = init_this.getParent();
		        		var search_view = this_parent.searchview;
			            var search_data = search_view.build_search_data();
			            var action = this_parent.action;
			            var action_domain = action.domain;
			            var action_context = action.context;
			            
		        		if (event.target.id == "button_open_owner_filter"){
			        		self = this;
			        		
			        		rpc.query({
					                model: active_model,
					                method: 'get_avail_owners',
					                args: [false, search_data.domains, action_domain, action_context],
					            }, {
					                timeout: 5000,
					                shadow: true,
					            })
					            .then(function(result){
				    	    		init_this.owners = result;
				    	    		var owner_filter_dropdown_html = '<li><input type="checkbox" value="" />Empty</li><hr/>'
				    	    		for (var i=0; i < result.length; i++) { 
				    	    			owner_filter_dropdown_html += '<li><input type="checkbox" value="'+result[i][0]+'" />'+result[i][1]+'</li>'
				    	    		}
				    	    			
				    	    		var dropdown_container = $(self)[0].children[1];
				    	    		var dropdown_container_list = dropdown_container.children[1];
				    	    		
				    	    		dropdown_container_list.innerHTML = owner_filter_dropdown_html;
					            }, function(type,err){}
				            );

		        		}else if (event.target.id == "accept_filter") {
		        			self = this;
		        			var owners = $(self).find('li');
		        			var owner_filters = []
		        			for (var i=0; i < owners.length; i++) { 
		        				if (owners[i].nodeName != 'LI'){
		        					continue;
		        				}
		        				
		        				if (owners[i].firstElementChild.checked == true){
		        			        var new_attr = {};
		        			        var owner_code = owners[i].children[0].value;
		        			        var owner_name = owners[i].children[0].nextSibling.textContent;
		        			        new_attr.tag = 'filter';
		        			        new_attr.children=[];
		        			        new_attr.attrs = {};
		        			        if (owner_code){
			        			        new_attr.attrs.domain = [['owner_id.owner_code','=',owner_code]];
			        			        new_attr.attrs.string = "Owner is "+owner_name;
		        			        } else {
			        			        new_attr.attrs.domain = [['owner_id.owner_code','=',false]];
			        			        new_attr.attrs.string = "Owner is empty";
		        			        }
		        			        owner_filters.push(new_attr);
		        				};
		        			};
		        	        var  filters_widgets = _.map(owner_filters, function (filter) {
		                        return new search_inputs.Filter(filter, this);
		                    });
		        	        var filter_group = new search_inputs.FilterGroup(filters_widgets, search_view),
		                    facets = filters_widgets.map(function (filter) {
		                        return filter_group.make_facet([filter_group.make_value(filter)]);
		                    });
		        	        
		        	        filter_group.insertBefore(this.$add_filter);
		        	        $('<li class="divider">').insertBefore(this.$add_filter);
		        	        search_view.query.add(facets, {silent: true});
		        	        search_view.query.trigger('reset');

		        		};
		        		
		        		var childs = self.parentNode.children;
			    		var childs_obj = $(childs);
			    		childs_obj.each(function () {
			    			var class_list = this.classList;
			    			if (class_list.contains('dropdown') && class_list.contains('open') && this != self){
			    				$(this).toggleClass('open');
			    			};
				        });
		        		$(self).toggleClass('open');
		        	} // jei prireiktu to elif'o apacioje, sita nutrinti
//		        	}else if (event.target && event.target.nodeName == "INPUT"){
//		        		console.log("event.target: ", event.target);
//		        	};
		        	
		        });
	        }else{
	            if (typeof(owner_filter_dropdown[0]) != 'undefined' && owner_filter_dropdown[0] != null){
	            	owner_filter_dropdown[0].hidden = true;
	            };
	        };
	        
	        
	        
	        
	        
	        
	        
//************************************************************************************************       
//******************************** SIUNTIMO SANDELIU FILTRAS *************************************
//************************************************************************************************
  	       
  	        if (shipping_warehouse_filter_objs.hasOwnProperty(active_model)){
  	            if (typeof(shipping_warehouse_filter_dropdown[0]) != 'undefined' && shipping_warehouse_filter_dropdown[0] != null){
  	            	shipping_warehouse_filter_dropdown[0].style.display = 'inline-block';
  	            	shipping_warehouse_filter_dropdown[0].style.position = 'relative';
  	            };

  	        	
  	        	shipping_warehouse_filter_dropdown.on('click', function (event) {
  		        	if (event.target && event.target.nodeName == "BUTTON"){
		        		var this_parent = init_this.getParent();
		        		var search_view = this_parent.searchview;
			            var search_data = search_view.build_search_data();
			            var action = this_parent.action;
			            var action_domain = action.domain;
			            var action_context = action.context;
  			            
  			            var shipping_warehouse_field_name = shipping_warehouse_filter_objs[active_model].field_name;
  			            var shipping_warehouse_field_type = shipping_warehouse_filter_objs[active_model].field_type;
  			            
  		        		if (event.target.id == "button_open_shipping_warehouse_filter"){
  			        		self = this;
  			        		rpc.query({
  					                model: active_model,
  					                method: 'get_avail_shipping_warehouses',
					                args: [false, search_data.domains, action_domain, action_context],
  					            }, {
  					                timeout: 5000,
  					                shadow: true,
  					            })
  					            .then(function(result){
  				    	    		init_this.shipping_warehouses = result;
  				    	    		var shipping_warehouse_filter_dropdown_html = '<li><input type="checkbox" value="" />Empty</li><hr/>'
  				    	    			
  				    	    		if (shipping_warehouse_field_type == 'str'){		
	  				    	    		for (var i=0; i < result.length; i++) { 
	  				    	    			shipping_warehouse_filter_dropdown_html += '<li><input type="checkbox" value="'+result[i]+'" />'+result[i]+'</li>'
	  				    	    		}
  				    	    		} else{
  				    	    			for (var i=0; i < result.length; i++) { 
	  				    	    			shipping_warehouse_filter_dropdown_html += '<li><input type="checkbox" value="'+result[i][0]+'" />'+result[i][1]+'</li>'
	  				    	    		}
  				    	    		}
  				    	    		
  				    	    		var dropdown_container = $(self)[0].children[1];
				    	    		var dropdown_container_list = dropdown_container.children[1];
				    	    		
				    	    		dropdown_container_list.innerHTML = shipping_warehouse_filter_dropdown_html;
  					            }, function(type,err){}
  				            );

  		        		}else if (event.target.id == "accept_filter") {
  		        			self = this;
  		        			var shipping_warehouses = $(self).find('li');
  		        			var shipping_warehouses_filters = []
  		        			for (var i=0; i < shipping_warehouses.length; i++) { 
  		        				if (shipping_warehouses[i].nodeName != 'LI'){
  		        					continue;
  		        				}
  		        				
  		        				if (shipping_warehouses[i].firstElementChild.checked == true){
  		        			        var new_attr = {};
  		        			        new_attr.tag = 'filter';
  		        			        new_attr.children=[];
  		        			        new_attr.attrs = {};
  		        			        
  		        			        if (shipping_warehouse_field_type == 'str'){
  	  		        			        var shipping_warehouse_str = shipping_warehouses[i].children[0].value;
	  		        			        if (shipping_warehouse_str){
	  			        			        new_attr.attrs.domain = [[shipping_warehouse_field_name,'=',shipping_warehouse_str]];
	  			        			        new_attr.attrs.string = "Shipping Warehouses is "+shipping_warehouse_str;
	  		        			        } else {
	  			        			        new_attr.attrs.domain = [[shipping_warehouse_field_name,'=',false]];
	  			        			        new_attr.attrs.string = "Shipping Warehouses is empty";
	  		        			        }
  		        			        } else {
  			        			        var shipping_warehouse_id = parseInt(shipping_warehouses[i].children[0].value);
  			        			        var shipping_warehouse_name = shipping_warehouses[i].children[0].nextSibling.textContent;
  		        			        	if (shipping_warehouse_id){
	  			        			        new_attr.attrs.domain = [[shipping_warehouse_field_name,'=',shipping_warehouse_id]];
	  			        			        new_attr.attrs.string = "Shipping Warehouses is "+shipping_warehouse_name;
	  		        			        } else {
	  			        			        new_attr.attrs.domain = [[shipping_warehouse_field_name,'=',false]];
	  			        			        new_attr.attrs.string = "Shipping Warehouses is empty";
	  		        			        }
  		        			        }
  		        			        
  		        			        
  		        			        shipping_warehouses_filters.push(new_attr);
  		        				};
  		        			};
  		        	        var  filters_widgets = _.map(shipping_warehouses_filters, function (filter) {
  		                        return new search_inputs.Filter(filter, this);
  		                    });
  		        	        var filter_group = new search_inputs.FilterGroup(filters_widgets, search_view),
  		                    facets = filters_widgets.map(function (filter) {
  		                        return filter_group.make_facet([filter_group.make_value(filter)]);
  		                    });
  		        	        
  		        	        filter_group.insertBefore(this.$add_filter);
  		        	        $('<li class="divider">').insertBefore(this.$add_filter);
  		        	        search_view.query.add(facets, {silent: true});
  		        	        search_view.query.trigger('reset');

  		        		};
  		        		
  		        		var childs = self.parentNode.children;
  			    		var childs_obj = $(childs);
  			    		childs_obj.each(function () {
  			    			var class_list = this.classList;
  			    			if (class_list.contains('dropdown') && class_list.contains('open') && this != self){
  			    				$(this).toggleClass('open');
  			    			};
  				        });
  		        		$(self).toggleClass('open');
  		        	} // jei prireiktu to elif'o apacioje, sita nutrinti
//	      		        	}else if (event.target && event.target.nodeName == "INPUT"){
//	      		        		console.log("event.target: ", event.target);
//	      		        	};
  		        	
  		        });
  	        }else{
  	            if (typeof(shipping_warehouse_filter_dropdown[0]) != 'undefined' && shipping_warehouse_filter_dropdown[0] != null){
  	            	shipping_warehouse_filter_dropdown[0].hidden = true;
  	            };
  	        };
  	        
  	        
  	        
//************************************************************************************************       
//************************************* DATU FILTRAS *********************************************
//************************************************************************************************
	        	
  	       if (date_filter_objs.hasOwnProperty(active_model)){
  	    	   if (typeof(date_filter_dropdown[0]) != 'undefined' && date_filter_dropdown[0] != null){
	            	date_filter_dropdown[0].style.display = 'inline-block';
	            	date_filter_dropdown[0].style.position = 'relative';
	            };
	        	date_filter_dropdown.on('click', function (event) {
		        	if (event.target && event.target.nodeName == "BUTTON"){
		        		var this_parent = init_this.getParent();
		        		var search_view = this_parent.searchview;
			            var search_data = search_view.build_search_data();
			            var action = this_parent.action;
			            var action_domain = action.domain;
			            var action_context = action.context;

		        		if (event.target.id == "button_open_date_filter"){
			        		self = this;
			        		
			        		rpc.query({
					                model: active_model,
					                method: 'get_avail_dates',
					                args: [false, search_data.domains, action_domain, action_context],
					            }, {
					                timeout: 5000,
					                shadow: true,
					            })
					            .then(function(result){
				    	    		init_this.dates = result;
				    	    		var date_filter_dropdown_html = '<li><input type="checkbox" value="" />Empty</li><hr/>'
				    	    		for (var i=0; i < result.length; i++) { 
				    	    			date_filter_dropdown_html += '<li><input type="checkbox" value="'+result[i]+'" />'+result[i]+'</li>'
				    	    		}

				    	    		var dropdown_container = $(self)[0].children[1];
				    	    		var dropdown_container_list = dropdown_container.children[1];
				    	    		
				    	    		dropdown_container_list.innerHTML = date_filter_dropdown_html;
					            }, function(type,err){}
				            );

		        		}else if (event.target.id == "accept_filter") {
		        			self = this;
		        			var dates = $(self).find('li');
		        			var date_filters = []
		        			for (var i=0; i < dates.length; i++) { 
		        				if (dates[i].nodeName != 'LI'){
		        					continue;
		        				}
		        				
		        				if (dates[i].firstElementChild.checked == true){
		        			        var new_attr = {};
		        			        var selected_date = dates[i].children[0].value;
		        			        new_attr.tag = 'filter';
		        			        new_attr.children=[];
		        			        new_attr.attrs = {};
		        			        if (selected_date){
			        			        new_attr.attrs.domain = [[date_filter_objs[active_model],'=',selected_date]];
			        			        new_attr.attrs.string = "Date is "+selected_date;
		        			        } else {
			        			        new_attr.attrs.domain = [[date_filter_objs[active_model],'=',false]];
			        			        new_attr.attrs.string = "Date is empty";
		        			        }
		        			        date_filters.push(new_attr);
		        				};
		        			};
		        	        var  filters_widgets = _.map(date_filters, function (filter) {
		                        return new search_inputs.Filter(filter, this);
		                    });
		        	        var filter_group = new search_inputs.FilterGroup(filters_widgets, search_view),
		                    facets = filters_widgets.map(function (filter) {
		                        return filter_group.make_facet([filter_group.make_value(filter)]);
		                    });
		        	        
		        	        filter_group.insertBefore(this.$add_filter);
		        	        $('<li class="divider">').insertBefore(this.$add_filter);
		        	        search_view.query.add(facets, {silent: true});
		        	        search_view.query.trigger('reset');

		        		};
		        		
		        		var childs = self.parentNode.children;
			    		var childs_obj = $(childs);
			    		childs_obj.each(function () {
			    			var class_list = this.classList;
			    			if (class_list.contains('dropdown') && class_list.contains('open') && this != self){
			    				$(this).toggleClass('open');
			    			};
				        });
		        		$(self).toggleClass('open');
		        	} // jei prireiktu to elif'o apacioje, sita nutrinti
//  	    		        	}else if (event.target && event.target.nodeName == "INPUT"){
//  	    		        		console.log("event.target: ", event.target);
//  	    		        	};
		        	
		        });
	        }else{
	            if (typeof(date_filter_dropdown[0]) != 'undefined' && date_filter_dropdown[0] != null){
	            	date_filter_dropdown[0].hidden = true;
	            };
	        };

//************************************************************************************************
//************************************* DATU NUO IKI FILTRAS *********************************************
//************************************************************************************************

  	       if (date_from_to_filter_objs.hasOwnProperty(active_model)){
  	    	   if (typeof(date_from_filter_dropdown[0]) != 'undefined' && date_from_filter_dropdown[0] != null){
	            	date_from_filter_dropdown[0].style.display = 'inline-block';
	            	date_from_filter_dropdown[0].style.position = 'relative';
	           };
  	    	   if (typeof(date_to_filter_dropdown[0]) != 'undefined' && date_to_filter_dropdown[0] != null){
	            	date_to_filter_dropdown[0].style.display = 'inline-block';
	            	date_to_filter_dropdown[0].style.position = 'relative';
	           };
	            date_from_filter_dropdown.on('click', function (event) {
		        	if (event.target && event.target.nodeName == "BUTTON"){
		        		var this_parent = init_this.getParent();
		        		var search_view = this_parent.searchview;
			            var search_data = search_view.build_search_data();
			            var action = this_parent.action;
			            var action_domain = action.domain;
			            var action_context = action.context;

		        		if (event.target.id == "button_open_date_from_filter"){
			        		self = this;

			        		rpc.query({
					                model: active_model,
					                method: 'get_avail_dates',
					                args: [false, search_data.domains, action_domain, action_context],
					            }, {
					                timeout: 5000,
					                shadow: true,
					            })
					            .then(function(result){
				    	    		init_this.dates = result;
				    	    		var date_filter_from_dropdown_html = '<li><input type="checkbox" value="" />Empty</li><hr/>'
				    	    		for (var i=0; i < result.length; i++) {
				    	    			date_filter_from_dropdown_html += '<li><input type="checkbox" value="'+result[i]+'" />'+result[i]+'</li>'
				    	    		}

				    	    		var dropdown_container = $(self)[0].children[1];
				    	    		var dropdown_container_list = dropdown_container.children[1];

				    	    		dropdown_container_list.innerHTML = date_filter_from_dropdown_html;
					            }, function(type,err){}
				            );

		        		}else if (event.target.id == "accept_filter") {
		        			self = this;
		        			var dates = $(self).find('li');
		        			var date_filters = []
		        			for (var i=0; i < dates.length; i++) {
		        				if (dates[i].nodeName != 'LI'){
		        					continue;
		        				}

		        				if (dates[i].firstElementChild.checked == true){
		        			        var new_attr = {};
		        			        var selected_date = dates[i].children[0].value;
		        			        new_attr.tag = 'filter';
		        			        new_attr.children=[];
		        			        new_attr.attrs = {};
		        			        if (selected_date){
			        			        new_attr.attrs.domain = [[date_from_to_filter_objs[active_model],'>=',selected_date]];
			        			        new_attr.attrs.string = "Date is greater or equal "+selected_date;
		        			        } else {
			        			        new_attr.attrs.domain = [[date_from_to_filter_objs[active_model],'=',false]];
			        			        new_attr.attrs.string = "Date is empty";
		        			        }
		        			        date_filters.push(new_attr);
		        				};
		        			};
		        	        var  filters_widgets = _.map(date_filters, function (filter) {
		                        return new search_inputs.Filter(filter, this);
		                    });
		        	        var filter_group = new search_inputs.FilterGroup(filters_widgets, search_view),
		                    facets = filters_widgets.map(function (filter) {
		                        return filter_group.make_facet([filter_group.make_value(filter)]);
		                    });

		        	        filter_group.insertBefore(this.$add_filter);
		        	        $('<li class="divider">').insertBefore(this.$add_filter);
		        	        search_view.query.add(facets, {silent: true});
		        	        search_view.query.trigger('reset');

		        		};

		        		var childs = self.parentNode.children;
			    		var childs_obj = $(childs);
			    		childs_obj.each(function () {
			    			var class_list = this.classList;
			    			if (class_list.contains('dropdown') && class_list.contains('open') && this != self){
			    				$(this).toggleClass('open');
			    			};
				        });
		        		$(self).toggleClass('open');
		        	} // jei prireiktu to elif'o apacioje, sita nutrinti
//  	    		        	}else if (event.target && event.target.nodeName == "INPUT"){
//  	    		        		console.log("event.target: ", event.target);
//  	    		        	};

		        });
	            date_to_filter_dropdown.on('click', function (event) {
		        	if (event.target && event.target.nodeName == "BUTTON"){
		        		var this_parent = init_this.getParent();
		        		var search_view = this_parent.searchview;
			            var search_data = search_view.build_search_data();
			            var action = this_parent.action;
			            var action_domain = action.domain;
			            var action_context = action.context;

		        		if (event.target.id == "button_open_date_to_filter"){
			        		self = this;

			        		rpc.query({
					                model: active_model,
					                method: 'get_avail_dates',
					                args: [false, search_data.domains, action_domain, action_context],
					            }, {
					                timeout: 5000,
					                shadow: true,
					            })
					            .then(function(result){
				    	    		init_this.dates = result;
				    	    		var date_filter_to_dropdown_html = '<li><input type="checkbox" value="" />Empty</li><hr/>'
				    	    		for (var i=0; i < result.length; i++) {
				    	    			date_filter_to_dropdown_html += '<li><input type="checkbox" value="'+result[i]+'" />'+result[i]+'</li>'
				    	    		}

				    	    		var dropdown_container = $(self)[0].children[1];
				    	    		var dropdown_container_list = dropdown_container.children[1];

				    	    		dropdown_container_list.innerHTML = date_filter_to_dropdown_html;
					            }, function(type,err){}
				            );

		        		}else if (event.target.id == "accept_filter") {
		        			self = this;
		        			var dates = $(self).find('li');
		        			var date_filters = []
		        			for (var i=0; i < dates.length; i++) {
		        				if (dates[i].nodeName != 'LI'){
		        					continue;
		        				}

		        				if (dates[i].firstElementChild.checked == true){
		        			        var new_attr = {};
		        			        var selected_date = dates[i].children[0].value;
		        			        new_attr.tag = 'filter';
		        			        new_attr.children=[];
		        			        new_attr.attrs = {};
		        			        if (selected_date){
			        			        new_attr.attrs.domain = [[date_from_to_filter_objs[active_model],'<=',selected_date]];
			        			        new_attr.attrs.string = "Date is lesser or equal than "+selected_date;
		        			        } else {
			        			        new_attr.attrs.domain = [[date_from_to_filter_objs[active_model],'=',false]];
			        			        new_attr.attrs.string = "Date is empty";
		        			        }
		        			        date_filters.push(new_attr);
		        				};
		        			};
		        	        var  filters_widgets = _.map(date_filters, function (filter) {
		                        return new search_inputs.Filter(filter, this);
		                    });
		        	        var filter_group = new search_inputs.FilterGroup(filters_widgets, search_view),
		                    facets = filters_widgets.map(function (filter) {
		                        return filter_group.make_facet([filter_group.make_value(filter)]);
		                    });

		        	        filter_group.insertBefore(this.$add_filter);
		        	        $('<li class="divider">').insertBefore(this.$add_filter);
		        	        search_view.query.add(facets, {silent: true});
		        	        search_view.query.trigger('reset');

		        		};

		        		var childs = self.parentNode.children;
			    		var childs_obj = $(childs);
			    		childs_obj.each(function () {
			    			var class_list = this.classList;
			    			if (class_list.contains('dropdown') && class_list.contains('open') && this != self){
			    				$(this).toggleClass('open');
			    			};
				        });
		        		$(self).toggleClass('open');
		        	} // jei prireiktu to elif'o apacioje, sita nutrinti
//  	    		        	}else if (event.target && event.target.nodeName == "INPUT"){
//  	    		        		console.log("event.target: ", event.target);
//  	    		        	};

		        });
	        }else{
	            if (typeof(date_from_filter_dropdown[0]) != 'undefined' && date_from_filter_dropdown[0] != null){
	            	date_from_filter_dropdown[0].hidden = true;
	            };
	            if (typeof(date_to_filter_dropdown[0]) != 'undefined' && date_to_filter_dropdown[0] != null){
	            	date_to_filter_dropdown[0].hidden = true;
	            };
	        };

    
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
		        	    framework.blockUI();
			        	rpc.query({
				                model: active_model,
				                method: create_route_objs[active_model],
				                args: [selected_ids],
				            }, {
				                timeout: 335000,
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
	            if (create_route_btn.length > 0 && typeof(create_route_btn[0]) != 'undefined' && create_route_btn[0] != null){
	            	create_route_btn.hide();
	            };
	            if (create_route_btn_separator.length > 0 && typeof(create_route_btn_separator[0]) != 'undefined' && create_route_btn_separator[0] != null){
	            	create_route_btn_separator.hide();
	            };
	        };


//************************************************************************************************
//******************************** MARSRUTU UŽDARAYOM MYGTUKAS ***********************************
//************************************************************************************************
	        if (ctx.hasOwnProperty('close_routes_btn') && ctx.close_routes_btn == true){
	            if (close_routes_btn.length > 0 && typeof(close_routes_btn[0]) != 'undefined' && close_routes_btn[0] != null){
	            	close_routes_btn[0].style.display = 'inline-block';
	            	close_routes_btn[0].style.position = 'relative';
	            };
		        var this_parent = init_this.getParent();
		        var search_view = this_parent.searchview;
	            close_routes_btn.on('click', function (event) {
		        	var selected_ids = init_this.getSelectedIds();
		        	if (selected_ids.length > 0){
		        	    framework.blockUI();
			        	rpc.query({
				                model: active_model,
				                method: close_routes_objs[active_model],
				                args: [selected_ids],
				            }, {
				                timeout: 555000,
				                shadow: true,
				            })
				            .then(function(result){
                                framework.unblockUI();
		        	            search_view.query.trigger('reset');
                                if (result){
                                    setTimeout(function() {init_this.do_action(result)}, 2000);
    //		        	            init_this.do_action(result);
                                }
				            }, function(type,err){
				                framework.unblockUI();
		        	            search_view.query.trigger('reset');
				            	if (err && err.data && err.data.message) {
				            	    alert(err.data.message);
				            	} else {
				            	    alert("TIMEOUT");
				            	}
				            }
			            );
		        	}

	            });

	        }else{
	            if (close_routes_btn.length > 0 && typeof(close_routes_btn[0]) != 'undefined' && close_routes_btn[0] != null){
	            	close_routes_btn.hide();
	            };
	            if (close_routes_btn_separator.length > 0 && typeof(close_routes_btn_separator[0]) != 'undefined' && close_routes_btn_separator[0] != null){
	            	close_routes_btn_separator.hide();
	            };
	        };

	        
//----- RENDER BUTTONS metodo pabaiga	        
	    }
	
	});
	
	
	
	
	
	
	
	
//----------- Padaryta, kad listo headeryje rodytu reiksmiu sumas (tik laukam, kurie turi SUM; taip pat kaip suma footeryje)
// ***** Dar papildomai padaryta, kad per konteksta butu galima paduoti lista lauku su atributu 'hide_unnecessary_header_sums'
// tada tokiem laukam sumas rodytu tik panaudojus filtra, arba tik pazymejus eilutes checkboxais (one2many ir many2many rodys visada)
	ListRender.include({
		_renderHeaderCell: function (node) {
			var self = this;
			var name = node.attrs.name;
	        var order = this.state.orderedBy;
	        var isNodeSorted = order[0] && order[0].name === name;
	        var field = this.state.fields[name];
	        var $th = $('<th>');
	        if (!field) {
	            return $th;
	        }
	        var description;
	        if (node.attrs.widget) {
	            description = this.state.fieldsInfo.list[name].Widget.prototype.description;
	        }
	        if (description === undefined) {
	            description = node.attrs.string || field.string;
	        }
	        
	        var ctx = this.state.getContext();
	        var this_node_field = node.attrs.name;
	        

	        if (
	        	ctx.hasOwnProperty('hide_unnecessary_header_sums')
	        	&& ctx.hide_unnecessary_header_sums.includes(this_node_field)
	        ){
	        	var always_show_sum = false;
	        }else{
	        	var always_show_sum = true;
	        }

	        if (node.hasOwnProperty('aggregate') && node.aggregate.hasOwnProperty('value')){
	        	var this_parent_parent = this.getParent().getParent();
	        	if (this_parent_parent && this_parent_parent.hasOwnProperty('searchview')){
		        	var search_view = this.getParent().getParent().searchview;
		            var search_data = search_view.build_search_data();
	        	}else{
	        		var search_data = false;
	        	}
	        	
	        	if (always_show_sum || !search_data || this.selection.length > 0 || (search_data.hasOwnProperty('domains') && search_data.domains.length > 0)){
		        	var field = self.state.fields[node.attrs.name];
	                var value = node.aggregate.value;
	                var formattedValue = field_utils.format[field.type](value, field, {
	                    escape: true,
	                });
	
	                formattedValue = "\n(".concat(formattedValue,")");
	                formattedValue = '<span style="color:red;">'.concat(formattedValue,"</span>");
	        	}
//	        	}else{
//	        		formattedValue = ''
//	        	}
	        }

	        $th
	            .text(description)
	            .append(formattedValue)
	            .data('name', name)
	            .toggleClass('o-sort-down', isNodeSorted ? !order[0].asc : false)
	            .toggleClass('o-sort-up', isNodeSorted ? order[0].asc : false)
	            .addClass(field.sortable && 'o_column_sortable');

	        if (field.type === 'float' || field.type === 'integer' || field.type === 'monetary') {
	            $th.css({textAlign: 'right'});
	        }

	        if (config.debug) {
	            var fieldDescr = {
	                field: field,
	                name: name,
	                string: description || name,
	                record: this.state,
	                attrs: node.attrs,
	            };
	            this._addFieldTooltip(fieldDescr, $th);
	        }

	        return $th;
		}
	});
	 

	
});