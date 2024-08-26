import datetime
import enum
import logging
from decimal import Decimal
from typing import Any, List, Dict

import boto3
from aws_lambda_powertools import Tracer
from botocore.exceptions import ClientError

from common.ddb_service.types_ import GetItemOutput, ScanOutput

tracer = Tracer()


class DynamoDbUtilsService:

    def __init__(self, logging_level=logging.INFO, logger=None):
        self.client = boto3.client('dynamodb')
        if logger:
            self.logger = logger
        else:
            self.logger = logging.getLogger('boto3')
            self.logger.setLevel(logging_level)

    def put_items(self, table: str, entries: Dict[str, Any]) -> Any:
        if not table:
            raise Exception('table name is required')

        try:
            if not entries or len(entries) == 0:
                return None

            ddb_data = self._serialize(entries)
            resp = self.client.put_item(
                TableName=table,
                Item=ddb_data
            )
            # todo: check if failed raise an error

            return resp
        except Exception as e:
            self.logger.error(f'table {table} put item failed -> {entries}: {e}')
            raise Exception(f'table {table} put item failed -> {entries}: {e}')

    @tracer.capture_method
    def batch_put_items(self, table_items: Dict[str, List[Dict[str, Any]]]) -> Any:
        if not table_items or len(table_items) == 0:
            return None

        for table_name, items in table_items.items():
            raws = [{'PutRequest': {'Item': self._serialize(item)}} for item in items]
            batch = []
            for raw in raws:
                batch.append(raw)
                if len(batch) == 25:
                    self.client.batch_write_item(RequestItems={table_name: batch})
                    batch = []

            if len(batch) > 0:
                self.client.batch_write_item(RequestItems={table_name: batch})

    def update_item(self, table: str, key: Dict[str, Any], field_name: str, value: Any):
        search_keys = self._serialize(key)
        value = self._convert(value)
        try:
            self.client.update_item(
                TableName=table,
                Key=search_keys,
                UpdateExpression=f"set {field_name} = :r",
                ExpressionAttributeValues={
                    ':r': value
                },
                ReturnValues="UPDATED_NEW"
            )
        except ClientError as e:
            self.logger.error('keys: %s -> %s: %s', key, field_name, value)
            raise Exception(
                f'dynamodb update failed with table {table}, key: {key}, field: {field_name}, value: {value}, error: {e}')

    def get_item(self, table: str, key_values: Dict[str, Any]) -> Dict[str, Any]:
        try:
            search_keys = self._serialize(key_values)

            resp = self.client.get_item(
                TableName=table,
                Key=search_keys
            )
            named_ = GetItemOutput(**resp)
            if 'Item' not in named_:
                return dict()
            res = self.deserialize(named_['Item'])
            return res
        except ClientError as e:
            self.logger.error(f'table {table} keys_values: {key_values}')
            raise Exception(f'table {table} get_item failed with keys_values: {key_values}, e: {e}')

    def query_latest_item(self, table: str, key_values: Dict[str, Any]) -> Dict[str, Any]:
        try:
            filter_expressions, expression_values = self._get_ddb_filter(key_values)

            resp = self.client.query(
                TableName=table,
                KeyConditionExpression=filter_expressions,
                ExpressionAttributeValues=expression_values,
                Limit=1,
            )
            named_ = ScanOutput(**resp)
            if 'Items' not in named_:
                return dict()
            res = self.deserialize(named_['Items'][0])
            return res
        except ClientError as e:
            self.logger.error(f'table {table} keys_values: {key_values}')
            raise Exception(f'table {table} get_item failed with keys_values: {key_values}, e: {e}')

    def query_items(self, table: str, key_values: Dict[str, Any], filters: Dict[str, Any] = None, limit: int = None,
                    last_evaluated_key=None):
        try:
            key_expressions, expression_values = self._get_ddb_filter(key_values)
            if not filters:
                if limit:
                    if last_evaluated_key:
                        resp = self.client.query(
                            TableName=table,
                            KeyConditionExpression=key_expressions,
                            ExpressionAttributeValues=expression_values,
                            ExclusiveStartKey=last_evaluated_key,
                            Limit=limit
                        )
                    else:
                        resp = self.client.query(
                            TableName=table,
                            KeyConditionExpression=key_expressions,
                            ExpressionAttributeValues=expression_values,
                            Limit=limit
                        )
                else:
                    scan_resp = self.client.query(
                        TableName=table,
                        KeyConditionExpression=key_expressions,
                        ExpressionAttributeValues=expression_values,
                    )
                    resp = scan_resp['Items']
                    while 'LastEvaluatedKey' in scan_resp:
                        scan_resp = self.client.query(
                            TableName=table,
                            KeyConditionExpression=key_expressions,
                            ExpressionAttributeValues=expression_values,
                            ExclusiveStartKey=scan_resp['LastEvaluatedKey']
                        )
                        resp.extend(scan_resp['Items'])

                    # scan the whole table, no LastEvaluatedKey returned
                    return resp
            else:
                filter_expressions, filter_expression_values = self._get_ddb_filter(filters=filters)
                expression_values.update(filter_expression_values)
                resp = self.client.query(
                    TableName=table,
                    KeyConditionExpression=key_expressions,
                    FilterExpression=filter_expressions,
                    ExpressionAttributeValues=expression_values,
                )

            named_ = ScanOutput(**resp)
            return named_['Items'], named_['LastEvaluatedKey'] if 'LastEvaluatedKey' in named_ else None
        except ClientError as e:
            self.logger.error(f'table {table} keys_values: {key_values}')
            raise Exception(f'table {table} get_item failed with keys_values: {key_values}, e: {e}')

    def _get_ddb_filter(self, filters: Dict[str, Any]):
        prepare_filter_expressions = []
        prefix = ':'
        expression_values = {}
        for key, val in filters.items():
            if isinstance(val, list):
                val_keys = ''
                i = 0
                for v in val:
                    k = f'{prefix}{key}{str(i)}'
                    i += 1
                    val_keys += f'{k}, '
                    expression_values[k] = self._convert(v)

                prepare_filter_expressions.append('{} in ({})'.format(key, val_keys[:len(val_keys) - 2]))
            else:
                prepare_filter_expressions.append('{} = {}'.format(key, prefix + key))
                expression_values[prefix + key] = self._convert(val)
        filter_expressions = ' AND '.join(prepare_filter_expressions)
        return filter_expressions, expression_values

    def scan(self, table: str, filters: Dict[str, Any] = None, last_evaluated_key=None, limit: int = None):
        if filters is None or len(filters) == 0:
            if limit:
                if last_evaluated_key:
                    resp = self.client.scan(
                        TableName=table,
                        ExclusiveStartKey=last_evaluated_key,
                        Limit=limit
                    )
                else:
                    resp = self.client.query(
                        TableName=table,
                        Limit=limit
                    )
            else:
                scan_resp = self.client.scan(
                    TableName=table,
                )
                resp = scan_resp['Items']
                while 'LastEvaluatedKey' in scan_resp:
                    scan_resp = self.client.scan(
                        TableName=table,
                        ExclusiveStartKey=scan_resp['LastEvaluatedKey']
                    )
                    resp.extend(scan_resp['Items'])

                return resp
        else:
            filter_expressions, expression_values = self._get_ddb_filter(filters)
            if last_evaluated_key:
                resp = self.client.scan(
                    TableName=table,
                    FilterExpression=filter_expressions,
                    ExpressionAttributeValues=expression_values,
                    ExclusiveStartKey=last_evaluated_key,
                    Limit=limit
                )
            elif limit:
                resp = self.client.scan(
                    TableName=table,
                    FilterExpression=filter_expressions,
                    ExpressionAttributeValues=expression_values,
                    Limit=limit
                )
            else:
                scan_resp = self.client.scan(
                    TableName=table,
                    FilterExpression=filter_expressions,
                    ExpressionAttributeValues=expression_values
                )
                resp = scan_resp['Items']
                while 'LastEvaluatedKey' in scan_resp:
                    scan_resp = self.client.scan(
                        TableName=table,
                        FilterExpression=filter_expressions,
                        ExpressionAttributeValues=expression_values,
                        ExclusiveStartKey=scan_resp['LastEvaluatedKey']
                    )
                    resp.extend(scan_resp['Items'])

                return resp

        named_ = ScanOutput(**resp)
        # FIXME: handle failures
        return named_['Items'], named_['LastEvaluatedKey'] if 'LastEvaluatedKey' in named_ else None

    def delete_item(self, table: str, keys: dict[str, Any]):
        keys = self._serialize(keys)
        self.client.delete_item(
            TableName=table,
            Key=keys
        )
        # FIXME: handle failures

    def close(self):
        self.client.close()

    @staticmethod
    def _serialize(entries: dict[str, Any], prefix: str = '') -> dict[str, Any]:
        if not dict:
            return {}
        result = dict()
        for key, val in entries.items():
            resolved_val = DynamoDbUtilsService._convert(val)
            if resolved_val:
                result["{}{}".format(prefix, key)] = resolved_val
        return result

    @staticmethod
    # serializer = boto3.dynamodb.types.TypeSerializer()
    # low_level_copy = {k: serializer.serialize(v) for k,v in python_data.items()}
    def _convert(val):
        if val is None:
            return None
        if isinstance(val, bytes):
            return {'B': val}
        if isinstance(val, bool):
            return {'BOOL': val}
        elif isinstance(val, list):
            val_arr = []
            for item in val:
                val_arr.append(DynamoDbUtilsService._convert(item))
            return {'L': val_arr}
        elif isinstance(val, float) or isinstance(val, int) or isinstance(val, Decimal):
            return {'N': str(val)}
        elif isinstance(val, str):
            return {'S': str(val)}
        elif isinstance(val, enum.Enum):
            return {'S': str(val.value)}
        elif isinstance(val, dict):
            res = {}
            for key, val in val.items():
                if val is not None:
                    res[key] = DynamoDbUtilsService._convert(val)

            return {'M': res}
        elif isinstance(val, datetime.datetime):
            return {'S': str(val)}
        else:
            raise Exception(f'unknown type {val} at type: {type(val)}')

    @staticmethod
    def deserialize(rows: dict[str, dict[str, Any]]) -> dict[str, Any]:
        boto3.resource('dynamodb')
        # To go from low-level format to python
        deserializer = boto3.dynamodb.types.TypeDeserializer()
        python_data = {k: deserializer.deserialize(v) for k, v in rows.items()}
        return python_data
