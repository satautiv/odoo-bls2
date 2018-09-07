odoo.define('config_sanitex_delivey.AbstractView', function (require) {
	"use strict";

	var AbstractView  = require('web.AbstractView');
    var Context = require('web.Context');

	AbstractView.include({

        // Papildymas dėl dinaminio laukelių palaikymo
        _loadSubviews: function (parent) {
            var self = this;
            var defs = [];
            if (this.loadParams && this.loadParams.fieldsInfo) {
                var fields = this.loadParams.fields;
                console.log('this.loadParams', this.loadParams);
                _.each(this.loadParams.fieldsInfo.form, function (attrs, fieldName) {
                    if (fieldName.startsWith("related_move_ids_")){
                        var field = fields['related_move_ids'];
                    } else {
                        var field = fields[fieldName];
                    }
                    if (field.type !== 'one2many' && field.type !== 'many2many') {
                        return;
                    }

                    if (attrs.Widget.prototype.useSubview && !attrs.__no_fetch && !attrs.views[attrs.mode]) {
                        var context = {};
                        var regex = /'([a-z]*_view_ref)' *: *'(.*?)'/g;
                        var matches;
                        while (matches = regex.exec(attrs.context)) {
                            context[matches[1]] = matches[2];
                        }
                        defs.push(parent.loadViews(
                                field.relation,
                                new Context(context, self.userContext, self.loadParams.context),
                                [[null, attrs.mode === 'tree' ? 'list' : attrs.mode]])
                            .then(function (views) {
                                for (var viewName in views) {
                                    attrs.views[viewName] = views[viewName];
                                }
                                self._setSubViewLimit(attrs);
                            }));
                    } else {
                        self._setSubViewLimit(attrs);
                    }
                });
            }
            return $.when.apply($, defs);
        },
	});

});