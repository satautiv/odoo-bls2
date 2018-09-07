odoo.define('web.FormView', function (require) {
"use strict";

var BasicView = require('web.BasicView');
var Context = require('web.Context');
var core = require('web.core');
var FormController = require('web.FormController');
var FormRenderer = require('web.FormRenderer');

var _lt = core._lt;

var FormView = BasicView.extend({
    config: _.extend({}, BasicView.prototype.config, {
        Renderer: FormRenderer,
        Controller: FormController,
    }),
    display_name: _lt('Form'),
    icon: 'fa-edit',
    multi_record: false,
    searchable: false,
    viewType: 'form',
    /**
     * @override
     */
    init: function (viewInfo, params) {
        this._super.apply(this, arguments);

        var mode = params.mode || (params.currentId ? 'readonly' : 'edit');
        this.loadParams.type = 'record';

        this.controllerParams.disableAutofocus = params.disable_autofocus;
        this.controllerParams.hasSidebar = params.sidebar;
        this.controllerParams.toolbarActions = viewInfo.toolbar;
        this.controllerParams.footerToButtons = params.footer_to_buttons;
        if ('action' in params && 'flags' in params.action) {
            this.controllerParams.footerToButtons = params.action.flags.footer_to_buttons;
        }
        var defaultButtons = 'default_buttons' in params ? params.default_buttons : true;
        this.controllerParams.defaultButtons = defaultButtons;
        this.controllerParams.mode = mode;

        this.rendererParams.mode = mode;
//        this.keydown_escapes = function (event) {
//            if (event.keyCode === 13) {
//                event.stopPropagation()
//                console.log("PASPAUDEM ENTER 32", event, viewInfo, params, self, $('button[name="check"]'));
//                $('button[name="check"]').trigger('click')
//                $(document).off('keyup', summernote_mousedown);
//            }
//            if (event.keyCode === 27) {
//                console.log("PASPAUDEM ESC")
//                //self.close();
//            }
//        };
//        $(document).on('keydown', this.keydown_escape);
        console.log('INIT', this);
//        if (this.controllerParams.modelName && this.controllerParams.modelName in [])
//        $(document).on('keyup', this.keydown_escapes);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    getController: function (parent) {
        return this._loadSubviews(parent).then(this._super.bind(this, parent));
    },
});

return FormView;

});
