# Qdrant Cloud Migration Guide

This guide will help you migrate from local Qdrant to Qdrant Cloud for your AskBucky application.

## ✅ Configuration Changes Made

The following configuration files have been updated to use Qdrant Cloud:

1. **`config/config_retrieval.yaml`**
   - Changed `write_endpoint` from `qdrant_local` to `qdrant_cloud`
   - Disabled `qdrant_local` endpoint
   - Enabled `qdrant_cloud` endpoint (renamed from `qdrant_url`)

2. **`config/config_conv_store.yaml`**
   - Changed `default_storage` from `qdrant_local` to `qdrant_cloud`
   - Disabled `qdrant_local` storage
   - Enabled `qdrant_cloud` storage (renamed from `qdrant_remote`)

3. **`code/python/core/config.py`**
   - Updated fallback default storage to `qdrant_cloud`

4. **`code/python/automation/run_daily_load.sh`**
   - Updated database parameter from `qdrant_local` to `qdrant_cloud`

## 🔧 Manual Steps Required

### 1. Update Environment Variables

You need to manually update your `.env` file. The file is protected from automated editing, so please make these changes:

**Current settings:**
```bash
QDRANT_URL="http://localhost:6333"
QDRANT_API_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIn0.3P6C_8DARSfPalcpH27y0csxJ45kDas_3zGv920kpAM
```

**Change to:**
```bash
QDRANT_URL=https://7c19fb51-0395-405e-a696-6c05e6e1fe7d.us-east4-0.gcp.cloud.qdrant.io
QDRANT_API_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIn0.3P6C_8DARSfPalcpH27y0csxJ45kDas_3zGv920kpAM
```

### 2. Test Qdrant Cloud Connection

Run the test script to verify your Qdrant Cloud connection:

```bash
cd NLWeb
python test_qdrant_cloud.py
```

This script will:
- Connect to your Qdrant Cloud instance
- Create a test collection
- Insert test data
- Perform a search
- Clean up test data

### 3. Migrate Existing Data (Optional)

If you have existing data in your local Qdrant that you want to preserve, run the migration script:

```bash
cd NLWeb
python migrate_to_qdrant_cloud.py
```

This script will:
- Connect to both local and cloud Qdrant instances
- Migrate all collections and data
- Verify the migration was successful

**Note:** Only run this if you want to preserve existing data. If you're starting fresh, you can skip this step.

## 🚀 Testing Your Application

After making the changes:

1. **Test the connection:**
   ```bash
   cd NLWeb
   python test_qdrant_cloud.py
   ```

2. **Start your application:**
   ```bash
   cd NLWeb
   python code/python/app-aiohttp.py
   ```

3. **Test basic functionality:**
   - Try loading some data
   - Test search functionality
   - Verify conversation storage works

## 🔍 Troubleshooting

### Common Issues

1. **Connection Errors**
   - Verify your Qdrant Cloud URL is correct
   - Check that your API key is valid
   - Ensure your network allows HTTPS connections

2. **Authentication Errors**
   - Verify your API key is correct
   - Check that your Qdrant Cloud account is active
   - Ensure you have the necessary permissions

3. **Collection Not Found**
   - Collections will be created automatically when needed
   - If migrating data, ensure the migration script completed successfully

### Debug Commands

Check your current configuration:
```bash
cd NLWeb/code/python
python -c "from core.config import CONFIG; print('Retrieval endpoint:', CONFIG.write_endpoint); print('Storage endpoint:', CONFIG.conversation_storage_default)"
```

Test individual components:
```bash
cd NLWeb/code/python
python testing/test_database_local.py  # Update this script to use qdrant_cloud
```

## 📊 Performance Considerations

### Qdrant Cloud Benefits
- **Scalability:** Automatic scaling based on usage
- **Reliability:** Managed infrastructure with high availability
- **Security:** Built-in security features and compliance
- **Maintenance:** No need to manage local infrastructure

### Cost Optimization
- Monitor your usage in the Qdrant Cloud dashboard
- Consider using different tiers based on your needs
- Set up alerts for usage thresholds

## 🔄 Rollback Plan

If you need to rollback to local Qdrant:

1. **Revert configuration files:**
   - Change `write_endpoint` back to `qdrant_local` in `config_retrieval.yaml`
   - Change `default_storage` back to `qdrant_local` in `config_conv_store.yaml`
   - Re-enable `qdrant_local` endpoints and disable `qdrant_cloud`

2. **Update environment variables:**
   - Change `QDRANT_URL` back to `"http://localhost:6333"`

3. **Restart your application**

## 📝 Next Steps

1. ✅ Update your `.env` file with the Qdrant Cloud URL
2. ✅ Test the connection using `test_qdrant_cloud.py`
3. ✅ Migrate data if needed using `migrate_to_qdrant_cloud.py`
4. ✅ Test your application functionality
5. ✅ Monitor performance and costs in Qdrant Cloud dashboard

## 🆘 Support

If you encounter issues:
1. Check the Qdrant Cloud documentation
2. Review the test script output for specific error messages
3. Verify your configuration matches the examples above
4. Check your network connectivity to the Qdrant Cloud endpoint

---

**Migration Status:** Configuration files updated ✅  
**Next Action:** Update `.env` file and test connection 