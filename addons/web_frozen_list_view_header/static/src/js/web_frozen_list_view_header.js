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

odoo.define('web_frozen_list_view_header', function (require) {
'use strict';

var ListRenderer = require('web.ListRenderer');

ListRenderer.include({
    _renderView: function () {
        var self = this;
        return this._super().done(function () {
            var form_field_length = self.$el.parents('.o_form_field').length;
            var scrollArea = $(".o_content")[0];
            function do_freeze () {
                self.$el.find('table.o_list_view').each(function () {
                    $(this).stickyTableHeaders({scrollableArea: scrollArea, fixedOffset: 0.1});
                });
            }

            if (form_field_length == 0) {
                do_freeze();
                $(window).unbind('resize', do_freeze).bind('resize', do_freeze);
            }
        });
    },
});

});