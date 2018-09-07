odoo.define('config_sanitex_delivey.BasicModel', function (require) {
	"use strict";
	
	var BasicModel  = require('web.BasicModel');

	var x2ManyCommands = {
	    // (0, virtualID, {values})
	    CREATE: 0,
	    create: function (virtualID, values) {
	        return [x2ManyCommands.CREATE, virtualID || false, values];
	    },
	    // (1, id, {values})
	    UPDATE: 1,
	    update: function (id, values) {
	        return [x2ManyCommands.UPDATE, id, values];
	    },
	    // (2, id[, _])
	    DELETE: 2,
	    delete: function (id) {
	        return [x2ManyCommands.DELETE, id, false];
	    },
	    // (3, id[, _]) removes relation, but not linked record itself
	    FORGET: 3,
	    forget: function (id) {
	        return [x2ManyCommands.FORGET, id, false];
	    },
	    // (4, id[, _])
	    LINK_TO: 4,
	    link_to: function (id) {
	        return [x2ManyCommands.LINK_TO, id, false];
	    },
	    // (5[, _[, _]])
	    DELETE_ALL: 5,
	    delete_all: function () {
	        return [5, false, false];
	    },
	    // (6, _, ids) replaces all linked records with provided ids
	    REPLACE_WITH: 6,
	    replace_with: function (ids) {
	        return [6, false, ids];
	    }
	};
	
// ---- ODOO branduolyje buvo palikta klaida, kad jei o2m lauke yra daugaiu irasu, nei numatytais limitas
// ir visom eilutem sukosi by default onchange'as, tai viskas nuluzdavo ties tomis eilutemis, kurios nebetilpo i vaizda
	BasicModel.include({
		_generateChanges: function (record, options) {
	    	if (!record || record == undefined){
	    		return {};
	    	}
	    	
	        options = options || {};
	        var viewType = options.viewType || record.viewType;
	        var changes;
	        if ('changesOnly' in options && !options.changesOnly) {
	            changes = _.extend({}, record.data, record._changes);
	        } else {
	            changes = _.extend({}, record._changes);
	        }
	        var withReadonly = options.withReadonly || false;
	        var commands = this._generateX2ManyCommands(record, {
	            changesOnly: 'changesOnly' in options ? options.changesOnly : true,
	            withReadonly: withReadonly,
	        });
	        for (var fieldName in record.fields) {
	            // remove readonly fields from the list of changes
	            if (!withReadonly && fieldName in changes || fieldName in commands) {
	                var editionViewType = record._editionViewType[fieldName] || viewType;
	                if (this._isFieldProtected(record, fieldName, editionViewType)) {
	                    delete changes[fieldName];
	                    continue;
	                }
	            }

	            // process relational fields and handle the null case
	            var type = record.fields[fieldName].type;
	            var value;
	            if (type === 'one2many' || type === 'many2many') {
	                if (commands[fieldName] && commands[fieldName].length) { // replace localId by commands
	                    changes[fieldName] = commands[fieldName];
	                } else { // no command -> no change for that field
	                    delete changes[fieldName];
	                }
	            } else if (type === 'many2one' && fieldName in changes) {
	                value = changes[fieldName];
	                changes[fieldName] = value ? this.localData[value].res_id : false;
	            } else if (type === 'reference' && fieldName in changes) {
	                value = changes[fieldName];
	                changes[fieldName] = value ?
	                    this.localData[value].model + ',' + this.localData[value].res_id :
	                    false;
	            } else if (type === 'char' && changes[fieldName] === '') {
	                changes[fieldName] = false;
	            } else if (changes[fieldName] === null) {
	                changes[fieldName] = false;
	            }
	        }

	        return changes;
	    },
	    
	    _generateX2ManyCommands: function (record, options) {
	        var self = this;
	        options = options || {};
	        var fields = record.fields;
	        if (options.fieldNames) {
	            fields = _.pick(fields, options.fieldNames);
	        }
	        var commands = {};
	        var data = _.extend({}, record.data, record._changes);
	        var type;
	        for (var fieldName in fields) {
	            type = fields[fieldName].type;

	            if (type === 'many2many' || type === 'one2many') {
	                if (!data[fieldName]) {
	                    // skip if this field is empty
	                    continue;
	                }
	                commands[fieldName] = [];
	                var list = this.localData[data[fieldName]];
	                if (options.changesOnly && (!list._changes || !list._changes.length)) {
	                    // if only changes are requested, skip if there is no change
	                    continue;
	                }
	                var oldResIDs = list.res_ids.slice(0);
	                var relRecordAdded = [];
	                var relRecordUpdated = [];
	                _.each(list._changes, function (change) {
	                    if (change.operation === 'ADD') {
	                        relRecordAdded.push(self.localData[change.id]);
	                    } else if (change.operation === 'UPDATE' && !self.isNew(change.id)) {
	                        // ignore new records that would have been updated
	                        // afterwards, as all their changes would already
	                        // be aggregated in the CREATE command
	                        relRecordUpdated.push(self.localData[change.id]);
	                    }
	                });
	                list = this._applyX2ManyOperations(list);
	                if (type === 'many2many' || list._forceM2MLink) {
	                    var relRecordCreated = _.filter(relRecordAdded, function (rec) {
	                        return typeof rec.res_id === 'string';
	                    });
	                    var realIDs = _.difference(list.res_ids, _.pluck(relRecordCreated, 'res_id'));
	                    // deliberately generate a single 'replace' command instead
	                    // of a 'delete' and a 'link' commands with the exact diff
	                    // because 1) performance-wise it doesn't change anything
	                    // and 2) to guard against concurrent updates (policy: force
	                    // a complete override of the actual value of the m2m)
	                    commands[fieldName].push(x2ManyCommands.replace_with(realIDs));
	                    _.each(relRecordCreated, function (relRecord) {
	                        var changes = self._generateChanges(relRecord, options);
	                        commands[fieldName].push(x2ManyCommands.create(relRecord.ref, changes));
	                    });
	                    // generate update commands for records that have been
	                    // updated (it may happen with editable lists)
	                    _.each(relRecordUpdated, function (relRecord) {
	                        var changes = self._generateChanges(relRecord, options);
	                        if (!_.isEmpty(changes)) {
	                            delete changes.id;
	                            var command = x2ManyCommands.update(relRecord.res_id, changes);
	                            commands[fieldName].push(command);
	                        }
	                    });
	                } else if (type === 'one2many') {
	                    var removedIds = _.difference(oldResIDs, list.res_ids);
	                    var addedIds = _.difference(list.res_ids, oldResIDs);
	                    var keptIds = _.intersection(oldResIDs, list.res_ids);

	                    // the didChange variable keeps track of the fact that at
	                    // least one id was updated
	                    var didChange = false;
	                    var changes, command, relRecord;
	                    for (var i = 0; i < list.res_ids.length; i++) {
	                        if (_.contains(keptIds, list.res_ids[i])) {
	                            // this is an id that already existed
	                            relRecord = _.findWhere(relRecordUpdated, {res_id: list.res_ids[i]});
	                            changes = relRecord ? this._generateChanges(relRecord, options) : {};
	                            if (!_.isEmpty(changes)) {
	                                delete changes.id;
	                                command = x2ManyCommands.update(relRecord.res_id, changes);
	                                didChange = true;
	                            } else {
	                                command = x2ManyCommands.link_to(list.res_ids[i]);
	                            }
	                            commands[fieldName].push(command);
	                        } else if (_.contains(addedIds, list.res_ids[i])) {
	                            // this is a new id (maybe existing in DB, but new in JS)
	                            relRecord = _.findWhere(relRecordAdded, {res_id: list.res_ids[i]});
	                            changes = this._generateChanges(relRecord, options);
	                            if (relRecord && relRecord != undefined){
		                            if ('id' in changes) {
		                                // the subrecord already exists in db
		                                delete changes.id;
		                                if (this.isNew(record.id)) {
		                                    // if the main record is new, link the subrecord to it
		                                    commands[fieldName].push(x2ManyCommands.link_to(relRecord.res_id));
		                                }
		                                if (!_.isEmpty(changes)) {
		                                    commands[fieldName].push(x2ManyCommands.update(relRecord.res_id, changes));
		                                }
		                            } else {
		                                // the subrecord is new, so create it
		                                commands[fieldName].push(x2ManyCommands.create(relRecord.ref, changes));
		                            }
	                            }
	                        }
	                    }
	                    if (options.changesOnly && !didChange && addedIds.length === 0 && removedIds.length === 0) {
	                        // in this situation, we have no changed ids, no added
	                        // ids and no removed ids, so we can safely ignore the
	                        // last changes
	                        commands[fieldName] = [];
	                    }
	                    // add delete commands
	                    for (i = 0; i < removedIds.length; i++) {
	                        if (list._forceM2MUnlink) {
	                            commands[fieldName].push(x2ManyCommands.forget(removedIds[i]));
	                        } else {
	                            commands[fieldName].push(x2ManyCommands.delete(removedIds[i]));
	                        }
	                    }
	                }
	            }
	        }
	        return commands;
	    },


        _getFieldNames: function (element) {
            var fieldsInfo = element.fieldsInfo;
            var fieldNames = Object.keys(fieldsInfo && fieldsInfo[element.viewType] || {});

            for (var i=0; i<fieldNames.length; i++){
                if (fieldNames[i].startsWith('related_move_ids_')){
                    fieldNames.splice(i, 1);
                }
            };
            return fieldNames;
        },


        _fetchRecord: function (record, options) {
            var self = this;
            var fieldNames = options && options.fieldNames || record.getFieldNames();
            fieldNames = _.uniq(fieldNames.concat(['display_name']));
            for (var i=0; i<fieldNames.length; i++){
                if (fieldNames[i].startsWith('related_move_ids_')){
                    fieldNames.splice(i, 1);
                }
            };

            return this._rpc({
                    model: record.model,
                    method: 'read',
                    args: [[record.res_id], fieldNames],
                    context: _.extend({}, record.getContext(), {bin_size: true}),
                })
                .then(function (result) {
                    if (result.length === 0) {
                        return $.Deferred().reject();
                    }
                    result = result[0];
                    record.data = _.extend({}, record.data, result);
                })
                .then(function () {
                    self._parseServerData(fieldNames, record, record.data);
                })
                .then(function () {
                    return $.when(
                        self._fetchX2Manys(record, options),
                        self._fetchReferences(record)
                    ).then(function () {
                        return self._postprocess(record, options);
                    });
                });
        },


    _fetchX2Manys: function (record, options) {
        var self = this;
        var defs = [];
        var fieldNames = options && options.fieldNames || record.getFieldNames();
        for (var i=0; i<fieldNames.length; i++){
            if (fieldNames[i].startsWith('related_move_ids_')){
                fieldNames.splice(i, 1);
            }
        };
        var viewType = options && options.viewType || record.viewType;
        _.each(fieldNames, function (fieldName) {
            var field = record.fields[fieldName];
            if (field.type === 'one2many' || field.type === 'many2many') {
                var fieldInfo = record.fieldsInfo[viewType][fieldName];
                var rawContext = fieldInfo && fieldInfo.context;
                var view = fieldInfo.views && fieldInfo.views[fieldInfo.mode];
                var fieldsInfo = view ? view.fieldsInfo : (fieldInfo.fieldsInfo || {});
                var ids = record.data[fieldName] || [];
                var list = self._makeDataPoint({
                    count: ids.length,
                    context: record.context,
                    fieldsInfo: fieldsInfo,
                    fields: view ? view.fields : fieldInfo.relatedFields,
                    limit: fieldInfo.limit,
                    modelName: field.relation,
                    res_ids: ids,
                    static: true,
                    type: 'list',
                    orderedBy: fieldInfo.orderedBy,
                    parentID: record.id,
                    rawContext: rawContext,
                    relationField: field.relation_field,
                    viewType: view ? view.type : fieldInfo.viewType,
                });
                record.data[fieldName] = list.id;
                if (!fieldInfo.__no_fetch) {
                    var def = self._readUngroupedList(list).then(function () {
                        return $.when(
                            self._fetchX2ManysBatched(list),
                            self._fetchReferencesBatched(list)
                        );
                    });
                    defs.push(def);
                }
            }
        });
        return $.when.apply($, defs);
    },

	});
});