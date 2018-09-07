odoo.define('config_sanitex_delivey.FormRenderer', function (require) {
	"use strict";
	
	var FormRenderer  = require('web.FormRenderer');
	var rpc = require('web.rpc');
	
	FormRenderer.include({
		// Uzklota, kad sukurus arparedagavus irasa su verciamu laukeliu,
		// nemestu notificationu siulanciu atlikti vertimus
		displayTranslationAlert: function (alertFields) {},
		
		// Padaryta, akd vaizduose ant page butu galima prideti atributa "info_field" ir nurodant kazkoki laukeli
		// tada po tab'o pavadinimo rasys to laukelio reiksme
		_renderTabHeader: function (page, page_id) {
	        var $a = $('<a>', {
	            'data-toggle': 'tab',
	            disable_anchor: 'true',
	            href: '#' + page_id,
	            role: 'tab',
	            text: page.attrs.string,
	        });
	    	
	        if (page.attrs.hasOwnProperty('info_field') && this.state.data.hasOwnProperty(page.attrs.info_field)){
	        	var info_field_name = page.attrs.info_field;
	        	var data = this.state.data;
	        	
		    	var formattedValue = data[info_field_name];
		        formattedValue = " (".concat(formattedValue,")");
		    	formattedValue = '<span style="color:red;">'.concat(formattedValue,"</span>");
		        $a.append(formattedValue)
	        }

	        if (page.attrs.hasOwnProperty('info_field_name') && this.state.data.hasOwnProperty(page.attrs.info_field_name)){
	        	var info_field_name = page.attrs.info_field_name;
	        	var data = this.state.data;

		    	var formattedValue = data[info_field_name];
//		        formattedValue = " (".concat(formattedValue,")");
		    	formattedValue = '<span>'.concat(formattedValue,"</span>");
		        $a.append(formattedValue)
	        }
	        
	        return $('<li>').append($a);
	    },



        // Papildymas dėl dinaminio laukelių ir tabų palaikymo
	    _renderTagNotebook: function (node) {

            var self = this;
            var $headers = $('<ul class="nav nav-tabs">');
            var $pages = $('<div class="tab-content nav nav-tabs">');
            var autofocusTab = -1;
            // renderedTabs is used to aggregate the generated $headers and $pages
            // alongside their node, so that their modifiers can be registered once
            // all tabs have been rendered, to ensure that the first visible tab
            // is correctly activated

            if (node.hasOwnProperty('attrs')){
                if (node.attrs.hasOwnProperty('dynamic_tags_by') && node.attrs.dynamic_tags_by == 'related_moves'){
                    if (self.hasOwnProperty('state')){
                        if (self.state.hasOwnProperty('data')){
                            if (self.state.data.related_picking_ids){
                                var fieldNames = Object.keys(self.state.fieldsInfo.form);
                                for(var j=0;j<fieldNames.length;j++){
                                    var fieldName = fieldNames[j];
                                    if(fieldName.startsWith("related_move_ids_")){
                                        if (Object.prototype.hasOwnProperty.call(self.state.fieldsInfo.form, fieldName)){
                                            delete self.state.fieldsInfo.form[fieldName];
                                        };
                                        if (Object.prototype.hasOwnProperty.call(self.state.fields, fieldName)){
                                            delete self.state.fields[fieldName];
                                        };
                                        if (Object.prototype.hasOwnProperty.call(self.state.data, fieldName)){
                                            delete self.state.data[fieldName];
                                        };
                                        while (node.children.length > 1){
                                            node.children.splice(0, 1);
                                        };
                                        node.children[0].attrs.string = "";
                                        node.children[0].children[0].attrs.name = "related_move_ids";
                                    }
                                };
                                for(var i = 0 ; i < self.state.data.related_picking_ids.data.length ; i++){
                                    var picking_number = self.state.data.related_picking_ids.data[i].data.name;
                                    var move_field_number = "related_move_ids" + "_" + picking_number;
                                    if (Object.prototype.hasOwnProperty.call(self.state.fieldsInfo.form, move_field_number)){
                                        delete self.state.fieldsInfo.form[move_field_number];
                                    };
                                    if (Object.prototype.hasOwnProperty.call(self.state.fields, move_field_number)){
                                        delete self.state.fields[move_field_number];
                                    };
                                    if (Object.prototype.hasOwnProperty.call(self.state.data, move_field_number)){
                                        delete self.state.data[move_field_number];
                                    };
                                    while (node.children.length > 1){
                                        node.children.splice(0, 1);
                                    };
                                    node.children[0].attrs.string = "";
                                    node.children[0].children[0].attrs.name = "related_move_ids";

                                }

                                for (var i = 0 ; i < self.state.data.related_picking_ids.data.length ; i++) {
                                    var already_exsist = false;
                                    var tab_name = "";
                                    for (var j = 0; j < node.children.length; j++){
                                        if (node.children[j].attrs.string == self.state.data.related_picking_ids.data[i].data.name){
                                            already_exsist = true;
                                            tab_name = self.state.data.related_picking_ids.data[i].data.name;
                                        };
                                    };
                                    if (!already_exsist){
                                        if (node.children[0].attrs.string != ""){
                                            var copy = jQuery.extend(true, {}, node.children[0]);
                                            if (copy.hasOwnProperty('attrs') && copy.attrs.hasOwnProperty('string')){
                                                copy.attrs.string = self.state.data.related_picking_ids.data[i].data.name
                                                copy.children[0].attrs.name = "related_move_ids" + "_" + self.state.data.related_picking_ids.data[i].data.name
                                                var new_field = jQuery.extend(true, {}, self.state.fields.related_move_ids);
                                                self.state.fields[copy.children[0].attrs.name] = new_field;

                                                var new_field_info = jQuery.extend(true, {}, self.state.fieldsInfo.form.related_move_ids);
                                                new_field_info.name = copy.children[0].attrs.name;
                                                self.state.fieldsInfo.form[new_field_info.name] = new_field_info;

                                                var new_field_data = jQuery.extend(true, {}, self.state.data.related_move_ids);
                                                self.state.data[new_field_info.name] = new_field_data;

                                                var ids_to_remove = []
                                                for (var k = 0; k < new_field_data.data.length ; k++){
                                                    if (new_field_data.data[k].data.reference != self.state.data.related_picking_ids.data[i].data.name){
                                                        ids_to_remove.push(new_field_data.data[k].data.id)
                                                    }
                                                }
                                                for (var k = 0; k < ids_to_remove.length ; k++){
                                                    var index = new_field_data.res_ids.indexOf(ids_to_remove[k]);
                                                    if (index > -1) {
                                                      new_field_data.res_ids.splice(index, 1);
                                                    }

                                                    var index2 = -1
                                                    for (var p = 0; p < new_field_data.data.length ; p++){
                                                        if (new_field_data.data[p].res_id == ids_to_remove[k]){
                                                            index2 = p
                                                        }
                                                    }

                                                    if (index2 > -1) {
                                                      new_field_data.data.splice(index2, 1);
                                                    }
                                                }
                                            };
                                            node.children.push(copy);
                                        } else {
                                            node.children[0].attrs.string = self.state.data.related_picking_ids.data[i].data.name
                                            node.children[0].children[0].attrs.name = "related_move_ids" + "_" + self.state.data.related_picking_ids.data[i].data.name
                                            var new_field = jQuery.extend(true, {}, self.state.fields.related_move_ids);
                                            self.state.fields[node.children[0].children[0].attrs.name] = new_field;

                                            var new_field_info = jQuery.extend(true, {}, self.state.fieldsInfo.form.related_move_ids);
                                            new_field_info.name = node.children[0].children[0].attrs.name;
                                            self.state.fieldsInfo.form[new_field_info.name] = new_field_info;

                                            var new_field_data = jQuery.extend(true, {}, self.state.data.related_move_ids);
                                            self.state.data[new_field_info.name] = new_field_data;


                                            var ids_to_remove = []
                                            for (var k = 0; k < new_field_data.data.length ; k++){
                                                if (new_field_data.data[k].data.reference != self.state.data.related_picking_ids.data[i].data.name){
                                                    ids_to_remove.push(new_field_data.data[k].data.id)
                                                }
                                            }
                                            for (var k = 0; k < ids_to_remove.length ; k++){
                                                var index = new_field_data.res_ids.indexOf(ids_to_remove[k]);
                                                if (index > -1) {
                                                  new_field_data.res_ids.splice(index, 1);
                                                }

                                                var index2 = -1
                                                for (var p = 0; p < new_field_data.data.length ; p++){
                                                    if (new_field_data.data[p].res_id == ids_to_remove[k]){
                                                        index2 = p
                                                    }
                                                }

                                                if (index2 > -1) {
                                                  new_field_data.data.splice(index2, 1);
                                                }
                                            }
                                        }
                                    } else {
                                        var field_name = "related_move_ids" + "_" + tab_name;
                                        if (self.state.data.hasOwnProperty(field_name)){
                                            delete self.state.data[field_name]
                                        }
                                        if (self.state.data.hasOwnProperty(field_name)){
                                            var field_data = self.state.data[field_name];
                                            field_data.id = self.state.data["related_move_ids"].id
                                            for (var l = 0; l < self.state.data.related_move_ids.data.length ; l ++){
                                                var original_move = self.state.data.related_move_ids.data[l];
                                                if (original_move.data.reference == tab_name){
                                                    var copy_of_original_move = jQuery.extend(true, {}, original_move);
                                                    field_data.data.push(copy_of_original_move);
                                                    field_data.res_ids.push(copy_of_original_move.res_id);
                                                }
                                            }
                                        } else {

                                            var new_field_data = jQuery.extend(true, {}, self.state.data.related_move_ids);
                                            new_field_data.id = [];
                                            self.state.data[field_name] = new_field_data;
                                            var ids_to_remove = []
                                            for (var k = 0; k < new_field_data.data.length ; k++){
                                                if (new_field_data.data[k].data.reference != tab_name){
                                                    ids_to_remove.push(new_field_data.data[k].data.id)
                                                }
                                            }
                                            for (var k = 0; k < ids_to_remove.length ; k++){
                                                var index = new_field_data.res_ids.indexOf(ids_to_remove[k]);
                                                if (index > -1) {
                                                  new_field_data.res_ids.splice(index, 1);
                                                }

                                                var index2 = -1
                                                for (var p = 0; p < new_field_data.data.length ; p++){
                                                    if (new_field_data.data[p].res_id == ids_to_remove[k]){
                                                        index2 = p
                                                    }
                                                }

                                                if (index2 > -1) {
                                                  new_field_data.data.splice(index2, 1);
                                                }
                                            }
                                        }
                                    }
                                };
                            }
                        };
                    }
//                    node.children.shift()
                }
            }
//            rpc.query({
//                    model: active_model,
//                    method: 'show_print_button',
//                    args: [active_ids, context],
//                }, {
//                    timeout: 5000,
//                    shadow: true,
//                })
//                .then(function(result){
//                    if (result){
//                        $(print_dropdown_element).show();
//                    } else {
//                        $(print_dropdown_element).hide();
//                    };
//                }, function(type,err){
//                    $(print_dropdown_element).hide();
//                }
//            );
            var renderedTabs = _.map(node.children, function (child, index) {
                var pageID = _.uniqueId('notebook_page_');
                var $header = self._renderTabHeader(child, pageID);
                var $page = self._renderTabPage(child, pageID);
                if (autofocusTab === -1 && child.attrs.autofocus === 'autofocus') {
                    autofocusTab = index;
                }
                self._handleAttributes($header, child);
                $headers.append($header);
                $pages.append($page);
                return {
                    $header: $header,
                    $page: $page,
                    node: child,
                };
            });
            if (renderedTabs.length) {
                var tabToFocus = renderedTabs[Math.max(0, autofocusTab)];
                tabToFocus.$header.addClass('active');
                tabToFocus.$page.addClass('active');
            }
            // register the modifiers for each tab
            _.each(renderedTabs, function (tab) {
                self._registerModifiers(tab.node, self.state, tab.$header, {
                    callback: function (element, modifiers) {
                        // if the active tab is invisible, activate the first visible tab instead
                        if (modifiers.invisible && element.$el.hasClass('active')) {
                            element.$el.removeClass('active');
                            tab.$page.removeClass('active');
                            var $firstVisibleTab = $headers.find('li:not(.o_invisible_modifier):first()');
                            $firstVisibleTab.addClass('active');
                            $pages.find($firstVisibleTab.find('a').attr('href')).addClass('active');
                        }
                    },
                });
            });
            var $notebook = $('<div class="o_notebook">')
                    .data('name', node.attrs.name || '_default_')
                    .append($headers, $pages);
            this._registerModifiers(node, this.state, $notebook);
            this._handleAttributes($notebook, node);
            return $notebook;
        },
		
	});
});