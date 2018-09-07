//-*- coding: utf-8 -*-
//############################################################################
//
//   This module Copyright (C) 2018 MAXSNS Corp (http://www.maxsns.com)
//   Author: Henry Zhou (zhouhenry@live.com)
//
//   THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
//   OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
//   FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
//   THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
//   LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
//   FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
//   DEALINGS IN THE SOFTWARE.
//
//############################################################################

odoo.define('web_list_freeze_header', function (require) {
'use strict';

var ListRenderer = require('web.ListRenderer');
var dom = require('web.dom');

ListRenderer.include({
    _renderView: function () {
        var self = this;
        return this._super().done(function () {
            var form_field_length = self.$el.parents('.o_form_field').length;
            var scrollArea = $(".o_content")[0];
            function do_freeze () {
                self.$el.find('table.o_list_view').each(function () {
                    $(this).stickyTableHeaders({scrollableArea: scrollArea, fixedOffset: 0.1, ignore_dublicate_check: false});
                });
            }

            if (form_field_length == 0) {
                do_freeze();
                $(window).unbind('resize', do_freeze).bind('resize', do_freeze);
            }
        });
    },
	
    //Padaryta, kad pazymejus eiluciu checkboxus, persiskaiciuotu headeris
	_updateFooter: function () {
        var self = this;
        this._computeAggregates();
        
        console.log(this.$('thead'));
        
//        if (this.$('thead').length > 1){
//        	this.$('thead')[1].remove();
//        }
        
        while (this.$('thead').length > 1){
        	this.$('thead')[this.$('thead').length - 1].remove();
        }
        
        this.$('tfoot').replaceWith(this._renderFooter(!!this.state.groupedBy.length));
        this.$('thead').replaceWith(this._renderHeader(!!this.state.groupedBy.length));

        var scrollArea = $(".o_content")[0];

        function do_freeze () {
            self.$el.find('table.o_list_view').each(function () {
                $(this).stickyTableHeaders({scrollableArea: scrollArea, fixedOffset: 0.1, ignore_dublicate_check: true});
            });
        }

        do_freeze();
        $(window).unbind('resize', do_freeze).bind('resize', do_freeze);
    },
    
    
    //Pataisyta, kad teisingai veiktu perskaiciuoto headerio checkbox'as
    _renderSelector: function (tag) {
        var $content = dom.renderCheckbox();
        if (tag == 'th'){
        	var total_view_lines = this.state.res_ids.length;
        	if (total_view_lines > 0 && this.selection.length >= total_view_lines){
        		$content[0].firstChild.checked = true;
        	} else {
        		$content[0].firstChild.checked = false;
        	}
            
        }
        return $('<' + tag + ' width="1">')
                    .addClass('o_list_record_selector')
                    .append($content);
    },
});

});