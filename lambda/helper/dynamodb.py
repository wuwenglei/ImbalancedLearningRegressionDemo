# remove type capital letters introduced in dynamodb update_item in resampling
def remove_dynamodb_item_types(obj):
    chart_data_points = obj['chartDataPoints']['L'] if 'chartDataPoints' in obj else None
    resampling_start_time = obj['resamplingStartTime']['N'] if 'resamplingStartTime' in obj else None
    resampling_end_time = obj['resamplingEndTime']['N'] if 'resamplingEndTime' in obj else None
    on_resample_start_sns_publish_message_id = obj['onResampleStartSnsPublishMessageId']['S'] if 'onResampleStartSnsPublishMessageId' in obj else None
    on_resample_complete_sns_publish_message_id = obj['onResampleCompleteSnsPublishMessageId']['S'] if 'onResampleCompleteSnsPublishMessageId' in obj else None
    on_resample_fail_sns_publish_message_id = obj['onResampleFailSnsPublishMessageId']['S'] if 'onResampleFailSnsPublishMessageId' in obj else None
    obj.update({
        'chartDataPoints': chart_data_points,
        'resamplingStartTime': resampling_start_time,
        'resamplingEndTime': resampling_end_time,
        'onResampleStartSnsPublishMessageId': on_resample_start_sns_publish_message_id,
        'onResampleCompleteSnsPublishMessageId': on_resample_complete_sns_publish_message_id,
        'onResampleFailSnsPublishMessageId': on_resample_fail_sns_publish_message_id
    })
    return obj