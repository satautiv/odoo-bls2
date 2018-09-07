odoo.define('config_sanitex_delivey.relational_fields', function (require) {
	"use strict";

	var relational_fields = require('web.relational_fields');


    //padaryta kad padavus contexto parametrą open_search_dialog many2one laukelis iškart atidarytų paieškos dialogą
	relational_fields['FieldMany2One'].include({
        _onInputClick: function () {
            var self = this;
            var context = this.record.getContext(this.recordParams);
            var domain = this.record.getDomain(this.recordParams);

            if (context.hasOwnProperty('open_search_dialog') && context.open_search_dialog){
                self._rpc({
                    model: self.field.relation,
                    method: 'search',
                    kwargs: {
                        args: domain,
                        limit: null,
                        context: context,
                    },
                })
                .then(self._searchCreatePopup.bind(self, "search"));
            } else {
                if (this.$input.autocomplete("widget").is(":visible")) {
                    this.$input.autocomplete("close");
                } else if (this.floating) {
                    this.$input.autocomplete("search"); // search with the input's content
                } else {
                    this.$input.autocomplete("search", ''); // search with the empty string
                }
            }

        },
	});

});
