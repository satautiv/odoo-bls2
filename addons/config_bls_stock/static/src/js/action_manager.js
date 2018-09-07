odoo.define('config_bls_stock.ActionManager', function (require) {
	"use strict";
	
	var ActionManager = require('web.ActionManager');
	var ViewManager = require('web.ViewManager');
	var core = require('web.core');
	var dom = require('web.dom');
	var Widget = require('web.Widget');
//	var ViewManagerAction = require('web.ViewManagerAction');
	
	/**
	 * Class representing the actions of the ActionManager
	 * Basic implementation for client actions that are functions
	 */
	var Action = core.Class.extend({
	    init: function(action) {
	        this.action_descr = action;
	        this.title = action.display_name || action.name;
	    },
	    /**
	     * This method should restore this previously loaded action
	     * Calls on_reverse_breadcrumb_callback if defined
	     * @return {Deferred} resolved when widget is enabled
	     */
	    restore: function() {
	        if (this.on_reverse_breadcrumb_callback) {
	            return this.on_reverse_breadcrumb_callback();
	        }
	    },
	    /**
	     * There is nothing to detach in the case of a client function
	     */
	    detach: function() {
	    },
	    /**
	     * Destroyer: there is nothing to destroy in the case of a client function
	     */
	    destroy: function() {
	    },
	    /**
	     * Sets the on_reverse_breadcrumb_callback to be called when coming back to that action
	     * @param {Function} [callback] the callback
	     */
	    set_on_reverse_breadcrumb: function(callback) {
	        this.on_reverse_breadcrumb_callback = callback;
	    },
	    /**
	     * Not implemented for client actions
	     */
	    setScrollTop: function() {
	    },
	    /**
	     * Stores the DOM fragment of the action
	     * @param {jQuery} [$fragment] the DOM fragment
	     */
	    set_fragment: function($fragment) {
	        this.$fragment = $fragment;
	    },
	    /**
	     * Not implemented for client actions
	     * @return {int} the number of pixels the webclient is scrolled when leaving the action
	     */
	    getScrollTop: function() {
	        return 0;
	    },
	    /**
	     * @return {Object} the description of the action
	     */
	    get_action_descr: function() {
	        return this.action_descr;
	    },
	    /**
	     * @return {Object} dictionnary that will be interpreted to display the breadcrumbs
	     */
	    get_breadcrumbs: function() {
	        return { title: this.title, action: this };
	    },
	    /**
	     * @return {int} the number of views stacked, i.e. 0 for client functions
	     */
	    get_nb_views: function() {
	        return 0;
	    },
	    /**
	     * @return {jQuery} the DOM fragment of the action
	     */
	    get_fragment: function() {
	        return this.$fragment;
	    },
	    /**
	     * @return {string} the active view, i.e. empty for client actions
	     */
	    get_active_view: function() {
	        return '';
	    },
	});
	/**
	 * Specialization of Action for client actions that are Widgets
	 */
	var WidgetAction = Action.extend({
	    /**
	     * Initializes the WidgetAction
	     * Sets the title of the widget
	     */
	    init: function(action, widget) {
	        this._super(action);

	        this.widget = widget;
	        if (!this.widget.get('title')) {
	            this.widget.set('title', this.title);
	        }
	        this.widget.on('change:title', this, function(widget) {
	            this.title = widget.get('title');
	        });
	    },
	    /**
	     * Restores WidgetAction by calling do_show on its widget
	     */
	    restore: function() {
	        var self = this;
	        return $.when(this._super()).then(function() {
	            return self.widget.do_show();
	        });
	    },
	    /**
	     * Detaches the action's widget from the DOM
	     * @return the widget's $el
	     */
	    detach: function() {
	        // Hack to remove badly inserted nvd3 tooltips ; should be removed when upgrading nvd3 lib
	        $('body > .nvtooltip').remove();

	        return dom.detach([{widget: this.widget}]);
	    },
	    /**
	     * Destroys the widget
	     */
	    destroy: function() {
	        this.widget.destroy();
	    },
	});
//	/**
//	 * Specialization of WidgetAction for window actions (i.e. ViewManagers)
//	 */
	var ViewManagerAction = WidgetAction.extend({
	    /**
	     * Restores a ViewManagerAction
	     * Switches to the requested view by calling select_view on the ViewManager
	     * @param {int} [view_index] the index of the view to select
	     */
	    restore: function(view_index) {
	        var _super = this._super.bind(this);
	        return this.widget.select_view(view_index).then(function() {
	            return _super();
	        });
	    },
	    /**
	     * Sets the on_reverse_breadcrumb_callback and the scrollTop to apply when
	     * coming back to that action
	     * @param {Function} [callback] the callback
	     * @param {int} [scrollTop] the number of pixels to scroll
	     */
	    set_on_reverse_breadcrumb: function(callback, scrollTop) {
	        this._super(callback);
	        this.setScrollTop(scrollTop);
	    },
	    /**
	     * Sets the scroll position of the widgets's active_view
	     * @todo: replace this with a generic get/set local state mechanism.
	     * @see getScrollTop
	     *
	     * @override
	     * @param {integer} [scrollTop] the number of pixels to scroll
	     */
	    setScrollTop: function (scrollTop) {
	        var activeView = this.widget.active_view;
	        var viewController = activeView && activeView.controller;
	        if (viewController) {
	            viewController.setScrollTop(scrollTop);
	        }
	    },
	    /**
	     * Returns the current scrolling offset for the current action.  We have to
	     * ask nicely the question to the active view, because the answer depends
	     * on the view.
	     *
	     * @todo: replace this mechanism with a generic getLocalState and
	     * getLocalState.  Scrolling behaviour is only a part of what we might want
	     * to restore.
	     *
	     * @override
	     * @returns {integer} the number of pixels the webclient is currently
	     *  scrolled
	     */
	    getScrollTop: function () {
	        var activeView = this.widget.active_view;
	        var viewController = activeView && activeView.controller;
	        return viewController ? viewController.getScrollTop() : 0;
	    },
	    /**
	     * @return {Array} array of Objects that will be interpreted to display the breadcrumbs
	     */
	    get_breadcrumbs: function() {
	        var self = this;
	        var breadcrumbs_array = this.widget.view_stack.map(function (view, index) {
	            return {
	                title: view.controller && view.controller.get('title') || self.title,
	                index: index,
	                action: self,
	            };
	        });
	        return breadcrumbs_array;
	    },
	    /**
	     * @return {int} the number of views stacked in the ViewManager
	     */
	    get_nb_views: function() {
	        return this.widget.view_stack.length;
	    },
	    /**
	     * @return {string} the active view of the ViewManager
	     */
	    get_active_view: function() {
	        return this.widget.active_view.type;
	    }
	});
	
	ActionManager.include({

//		Uzklota, kad action context'e butu galima nurodyti, ar kurti langui breadcrumb'a
		push_action: function(widget, action_descr, options) {
	        var self = this;
	        var old_action_stack = this.action_stack;
	        var old_action = this.inner_action;
	        var old_widget = this.inner_widget;
	        var actions_to_destroy;
	        options = options || {};

	        // Empty action_stack or replace last action if requested
	        if (options.clear_breadcrumbs) {
	            actions_to_destroy = this.action_stack;
	            this.action_stack = [];
	        } else if (options.replace_last_action && this.action_stack.length > 0) {
	            actions_to_destroy = [this.action_stack.pop()];
	        }

	        // Instantiate the new action
	        var new_action;
	        if (widget instanceof ViewManager) {
	            new_action = new ViewManagerAction(action_descr, widget);
	        } else if (widget instanceof Widget) {
	            new_action = new WidgetAction(action_descr, widget);
	        } else {
	            new_action = new Action(action_descr);
	        }

	        // Set on_reverse_breadcrumb callback on previous inner_action
	        if (this.webclient && old_action) {
	            old_action.set_on_reverse_breadcrumb(options.on_reverse_breadcrumb, this.webclient.getScrollTop());
	        }

	        // Update action_stack (must be done before appendTo to properly
	        // compute the breadcrumbs and to perform do_push_state)
	        
	        var dont_create_breadcrumb = false;
	        
	        if (options.hasOwnProperty('action') && options.action != undefined){
		        var ctx = options.action.context;
		        if (ctx.hasOwnProperty('do_not_create_breadcrumb') && ctx.do_not_create_breadcrumb == true){
		        	dont_create_breadcrumb = true;
		        };
			};
	        
	        if (!dont_create_breadcrumb){
	        	this.action_stack.push(new_action);
	        };
	        
	        
	        this.inner_action = new_action;
	        this.inner_widget = widget;

	        if (widget.need_control_panel) {
	            // Set the ControlPanel bus on the widget to allow it to communicate its status
	            widget.set_cp_bus(this.main_control_panel.get_bus());
	        }

	        // render the inner_widget in a fragment, and append it to the
	        // document only when it's ready
	        var new_widget_fragment = document.createDocumentFragment();
	        return $.when(this.inner_widget.appendTo(new_widget_fragment)).done(function() {
	            // Detach the fragment of the previous action and store it within the action
	            if (old_action) {
	                old_action.set_fragment(old_action.detach());
	            }
	            if (!widget.need_control_panel) {
	                // Hide the main ControlPanel for widgets that do not use it
	                self.main_control_panel.do_hide();
	            }

	            // most of the time, the self.$el element should already be empty,
	            // because we detached the old action just a few line up.  However,
	            // it may happen that it is not empty, for example when a view
	            // manager was unable to load a view because of a crash.  In any
	            // case, this is done as a safety measure to avoid the 'double view'
	            // situation that we had when the web client was unable to recover
	            // from a crash.
	            self.$el.empty();

	            dom.append(self.$el, new_widget_fragment, {
	                in_DOM: self.is_in_DOM,
	                callbacks: [{widget: self.inner_widget}],
	            });
	            if (actions_to_destroy) {
	                self.clear_action_stack(actions_to_destroy);
	            }
	            self.toggle_fullscreen();
	            self.trigger_up('current_action_updated', {action: new_action});
	        }).fail(function () {
	            // Destroy failed action and restore internal state
	            new_action.destroy();
	            self.action_stack = old_action_stack;
	            self.inner_action = old_action;
	            self.inner_widget = old_widget;
	        });
	    },
	    
	});
	
});