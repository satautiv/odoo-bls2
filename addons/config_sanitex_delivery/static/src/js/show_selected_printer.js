odoo.define('config_sanitex_delivey.show_selected_printer', function (require) {
	"use strict";
	var SystrayMenu = require('web.SystrayMenu');
	var Widget = require('web.Widget');
	var session = require('web.session');
	var rpc = require('web.rpc');
    var core = require('web.core');


    var _t = core._t;
	
	var UserWarehouse = Widget.extend({
	    template:'config_sanitex_delivey.user_printer',
	    start: function () {
	    	var self = this;
	    	var main_self = this;
	    	
	    	this.show_printer_in_upper_menu();
	    	
	    	var dropdown = this.$el;
	    	
	    	dropdown.on('click', function (event) {
	    		self = this;
	    		if (event.target && event.target.nodeName == "A" && event.target.id == "a_open_printer_dropdown_menu"){
	    			
	    			rpc.query({
			                model: 'res.users',
			                method: 'get_available_printers',
			                args: [],
			            }, {
			                timeout: 3000,
			                shadow: true,
			            })
			            .then(function(result){
				    		if (result && result.length > 0 ) {
				    			var dropdown_html = '';
				    			for (var i=0; i < result.length; i++){ 
			    	    			dropdown_html += '<li><a href="#" id="'+result[i][0]+'">'+result[i][1]+'</a></li>';
			    	    		};
				    			$(self)[0].lastElementChild.innerHTML = dropdown_html;
				    		}
			            }, function(type,err){ }
		            );

	    		} else {
	    			rpc.query({
		                model: 'res.users',
		                method: 'select_printer',
		                args: [session.uid, parseInt(event.target.id)],
		            }, {
		                timeout: 3000,
		                shadow: true,
		            })
		            .then(function(result){
		            	main_self.show_printer_in_upper_menu();
		            }, function(type,err){}
	            );
	    			
	    		}

	    		//Kodo gabaliukas, kuris turetu uzdaryti kitus dropdownus
	    		var childs = self.parentNode.children;
	    		var childs_obj = $(childs);
	    		childs_obj.each(function () {
	    			var class_list = this.classList;
	    			if (class_list.contains('dropdown') && class_list.contains('open') && this != self){
	    				$(this).toggleClass('open');
	    			};
		        });
	    		
//	    		if ($(".open").length > 0) {
//	    			console.log("Atidarytaaaaaa!!!!");
//    			} else {
//    				console.log("Uzdarytaaaaaa!!!!");
//    			}
	    		$(self).toggleClass('open');
	    	});
	    	
	    	return this._super();
	    },
	    
	    show_printer_in_upper_menu : function(){
	    	var self = this;
	    	
	    	this.el.firstElementChild.style.color = '#ffffff';
	    	this.el.style.marginLeft = '30px';
	    	this.el.style.display = 'inline-block';
	    	
	    	rpc.query({
	                model: 'res.users',
	                method: 'read',
	                args: [session.uid, ['default_printer_id']],
	            }, {
	                timeout: 3000,
	                shadow: true,
	            })
	            .then(function(result){
		    		if (result && result.length > 0 && result[0].default_printer_id && result[0].default_printer_id.length > 1) {
		    			self.el.firstElementChild.textContent = '⎙ '+result[0].default_printer_id[1];
		    		}else{
		    			self.el.firstElementChild.textContent = _t("Printer is not selected");
		    		};
	            }, function(type,err){ self.el.firstElementChild.textContent = _t("Printer is not selected");}
            );
	    	
	    },
	});
	SystrayMenu.Items.push(UserWarehouse);
	
});